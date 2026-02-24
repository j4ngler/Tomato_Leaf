import os
import random
from collections import Counter
from typing import Dict, List, Tuple

import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms


class ImbalancedTomatoDataset(Dataset):
    """
    Dataset cho tập train:
    - Dựa trên ImageFolder gốc (base_dataset)
    - Chỉ dùng một tập con chỉ số (indices)
    - Áp dụng strong/weak augmentation khác nhau cho lớp ít và lớp nhiều.
    """

    def __init__(
        self,
        base_dataset: datasets.ImageFolder,
        indices: List[int],
        weak_transform: transforms.Compose,
        strong_transform: transforms.Compose,
        minority_classes: List[int],
    ) -> None:
        self.base_dataset = base_dataset
        self.indices = indices
        self.weak_transform = weak_transform
        self.strong_transform = strong_transform
        self.minority_classes = set(minority_classes)

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int):
        base_idx = self.indices[idx]
        path, target = self.base_dataset.samples[base_idx]

        image = self.base_dataset.loader(path)
        if target in self.minority_classes:
            image = self.strong_transform(image)
        else:
            image = self.weak_transform(image)

        return image, target


class SimpleSubsetDataset(Dataset):
    """
    Dataset đơn giản cho val/test:
    - Dùng chung ImageFolder gốc (base_dataset)
    - Chỉ lấy các chỉ số trong indices
    - Dùng một transform duy nhất (val/test transform).
    """

    def __init__(
        self,
        base_dataset: datasets.ImageFolder,
        indices: List[int],
        transform: transforms.Compose,
    ) -> None:
        self.base_dataset = base_dataset
        self.indices = indices
        self.transform = transform

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int):
        base_idx = self.indices[idx]
        path, target = self.base_dataset.samples[base_idx]
        image = self.base_dataset.loader(path)
        image = self.transform(image)
        return image, target


def stratified_split_indices(
    targets: List[int],
    val_split: float = 0.15,
    test_split: float = 0.15,
    seed: int = 42,
) -> Tuple[List[int], List[int], List[int]]:
    """
    Chia indices thành train/val/test theo từng lớp (stratified).
    """
    random.seed(seed)

    class_to_indices: Dict[int, List[int]] = {}
    for idx, label in enumerate(targets):
        class_to_indices.setdefault(label, []).append(idx)

    train_indices: List[int] = []
    val_indices: List[int] = []
    test_indices: List[int] = []

    for label, idxs in class_to_indices.items():
        idxs = idxs.copy()
        random.shuffle(idxs)

        n_total = len(idxs)
        n_val = int(n_total * val_split)
        n_test = int(n_total * test_split)
        n_train = n_total - n_val - n_test

        val_indices.extend(idxs[:n_val])
        test_indices.extend(idxs[n_val:n_val + n_test])
        train_indices.extend(idxs[n_val + n_test:n_val + n_test + n_train])

    random.shuffle(train_indices)
    random.shuffle(val_indices)
    random.shuffle(test_indices)

    return train_indices, val_indices, test_indices


def create_transforms(img_size: int = 256):
    """
    Tạo các transform cho train/val/test.
    - weak_transform: cho lớp nhiều (Yellow_Leaf_Curl_Virus)
    - strong_transform: cho lớp ít (Early_blight, Bacterial_spot)
    """
    weak_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
    ])

    strong_transform = transforms.Compose([
        transforms.Resize(int(img_size * 1.1)),
        transforms.RandomResizedCrop(img_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(degrees=20),
        transforms.ColorJitter(
            brightness=0.3,
            contrast=0.3,
            saturation=0.3,
            hue=0.1,
        ),
        transforms.RandomApply(
            [transforms.GaussianBlur(kernel_size=3)],
            p=0.3,
        ),
        transforms.ToTensor(),
    ])

    eval_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
    ])

    return weak_transform, strong_transform, eval_transform


def create_tomato_datasets(
    data_root: str,
    img_size: int = 256,
    val_split: float = 0.15,
    test_split: float = 0.15,
    seed: int = 42,
):
    """
    Tạo ra 3 dataset: train_dataset, val_dataset, test_dataset
    từ folder `data_root` có cấu trúc:
        data_root/
            Early_blight/
            Bacterial_spot/
            Yellow_Leaf_Curl_Virus/
    """
    if not os.path.isdir(data_root):
        raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu: {data_root}")

    # ImageFolder gốc (không transform, để tự xử lý transform trong Dataset wrapper)
    base_dataset = datasets.ImageFolder(root=data_root)

    print("classes:", base_dataset.classes)
    print("class_to_idx:", base_dataset.class_to_idx)

    targets = base_dataset.targets  # list nhãn (0,1,2,...)
    class_counts = Counter(targets)
    print("class_counts:", class_counts)

    # Chia indices train/val/test theo từng lớp
    train_indices, val_indices, test_indices = stratified_split_indices(
        targets,
        val_split=val_split,
        test_split=test_split,
        seed=seed,
    )

    print(f"Số mẫu train: {len(train_indices)}, val: {len(val_indices)}, test: {len(test_indices)}")

    weak_transform, strong_transform, eval_transform = create_transforms(img_size=img_size)

    # Xác định lớp ít (minority) dựa trên số lượng mẫu
    # Ở đây coi những lớp có số lượng <= median là "ít"
    counts_sorted = sorted(class_counts.items(), key=lambda x: x[1])
    _, median_count = counts_sorted[len(counts_sorted) // 2]
    minority_classes = [c for c, cnt in class_counts.items() if cnt <= median_count]

    print("minority_classes (index):", minority_classes)

    train_dataset = ImbalancedTomatoDataset(
        base_dataset=base_dataset,
        indices=train_indices,
        weak_transform=weak_transform,
        strong_transform=strong_transform,
        minority_classes=minority_classes,
    )

    val_dataset = SimpleSubsetDataset(
        base_dataset=base_dataset,
        indices=val_indices,
        transform=eval_transform,
    )

    test_dataset = SimpleSubsetDataset(
        base_dataset=base_dataset,
        indices=test_indices,
        transform=eval_transform,
    )

    return train_dataset, val_dataset, test_dataset, class_counts


def create_tomato_dataloaders(
    data_root: str,
    img_size: int = 256,
    batch_size: int = 32,
    val_split: float = 0.15,
    test_split: float = 0.15,
    seed: int = 42,
    num_workers: int = 4,
):
    """
    Tạo DataLoader cho train/val/test.
    - Train dùng WeightedRandomSampler để giảm lệch lớp.
    - Val/Test không dùng sampler, chỉ shuffle=False.
    """
    train_dataset, val_dataset, test_dataset, class_counts = create_tomato_datasets(
        data_root=data_root,
        img_size=img_size,
        val_split=val_split,
        test_split=test_split,
        seed=seed,
    )

    # Tính weights cho từng lớp từ tập train (dùng targets gốc theo indices train)
    base_targets = datasets.ImageFolder(root=data_root).targets
    # Lấy label của từng sample trong train theo chỉ số gốc
    # (indices chính là train_dataset.indices)
    train_labels = [base_targets[idx] for idx in train_dataset.indices]
    train_class_counts = Counter(train_labels)
    print("train_class_counts:", train_class_counts)

    num_classes = len(train_class_counts)
    class_sample_counts = [train_class_counts[i] for i in range(num_classes)]
    class_weights = [1.0 / c for c in class_sample_counts]

    sample_weights = [class_weights[label] for label in train_labels]
    sample_weights = torch.DoubleTensor(sample_weights)

    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(train_dataset),
        replacement=True,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        sampler=sampler,
        shuffle=False,
        num_workers=num_workers,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    # Ví dụ chạy nhanh để kiểm tra
    DATA_ROOT = r"D:\BkStar\TomatoLeaf\dataset"
    train_loader, val_loader, test_loader = create_tomato_dataloaders(
        data_root=DATA_ROOT,
        img_size=256,
        batch_size=32,
        val_split=0.15,
        test_split=0.15,
        seed=42,
        num_workers=4,
    )

    print("Số batch train:", len(train_loader))
    print("Số batch val:", len(val_loader))
    print("Số batch test:", len(test_loader))

