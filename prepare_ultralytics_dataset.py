import os
import random
import shutil
from collections import Counter
from typing import Dict, List, Optional

from PIL import Image
from torchvision import datasets, transforms

from dataloader import stratified_split_indices


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def copy_file(src: str, dst: str) -> None:
    ensure_dir(os.path.dirname(dst))
    shutil.copy2(src, dst)


def build_split_dirs(
    base_dataset: datasets.ImageFolder,
    split_indices: Dict[str, List[int]],
    out_root: str,
    oversample_train: bool = True,
) -> None:
    """
    Tạo cấu trúc thư mục cho Ultralytics:
        out_root/
          train/class_name/*.jpg
          val/class_name/*.jpg
          test/class_name/*.jpg

    - split_indices: dict với key 'train' | 'val' | 'test' -> list indices
    - Nếu oversample_train=True: oversample lớp ít trong train bằng cách copy file vật lý.
    """
    class_indices_train: Dict[int, List[int]] = {}
    train_idxs = split_indices.get("train", [])

    # Gom các index train theo lớp để oversample
    for idx in train_idxs:
        _, label = base_dataset.samples[idx]
        class_indices_train.setdefault(label, []).append(idx)

    # Thống kê số mẫu train hiện tại theo lớp
    train_class_counts = {c: len(idxs) for c, idxs in class_indices_train.items()}
    print("Số mẫu train ban đầu theo lớp:", train_class_counts)

    max_train_count = max(train_class_counts.values()) if train_class_counts else 0

    # Duyệt từng split
    for split_name, indices in split_indices.items():
        print(f"Đang xử lý split: {split_name}, số mẫu: {len(indices)}")

        if split_name == "train" and oversample_train and max_train_count > 0:
            # Tạo bản sao cân bằng cho train
            for class_idx, idxs in class_indices_train.items():
                class_name = base_dataset.classes[class_idx]

                # Copy bản gốc trước
                for idx in idxs:
                    src_path, _ = base_dataset.samples[idx]
                    filename = os.path.basename(src_path)
                    dst_path = os.path.join(out_root, split_name, class_name, filename)
                    copy_file(src_path, dst_path)

                # Oversample: copy thêm cho đến khi đạt ~max_train_count
                n_current = len(idxs)
                if n_current == 0:
                    continue

                n_target = max_train_count
                n_extra = n_target - n_current
                if n_extra <= 0:
                    continue

                print(f"Oversample lớp '{class_name}': thêm {n_extra} mẫu")

                # Lặp vòng qua idxs để copy thêm file
                extra_copies = 0
                round_idx = 0
                while extra_copies < n_extra:
                    base_idx = idxs[round_idx % n_current]
                    src_path, _ = base_dataset.samples[base_idx]
                    dirname, filename = os.path.split(src_path)
                    stem, ext = os.path.splitext(filename)

                    new_filename = f"{stem}_copy{extra_copies + 1}{ext}"
                    dst_path = os.path.join(out_root, split_name, class_name, new_filename)
                    copy_file(src_path, dst_path)

                    extra_copies += 1
                    round_idx += 1
        else:
            # Với val/test (hoặc train nếu không oversample): copy 1 lần mỗi file
            for idx in indices:
                src_path, label = base_dataset.samples[idx]
                class_name = base_dataset.classes[label]
                filename = os.path.basename(src_path)
                dst_path = os.path.join(out_root, split_name, class_name, filename)
                copy_file(src_path, dst_path)


def prepare_ultralytics_classification_dataset(
    src_root: str,
    out_root: str,
    val_split: float = 0.15,
    test_split: float = 0.15,
    seed: int = 42,
) -> None:
    """
    Từ dataset gốc dạng:
        src_root/
          Early_blight/
          Bacterial_spot/
          Yellow_Leaf_Curl_Virus/

    Tạo dataset mới cho Ultralytics dạng:
        out_root/
          train/<class>/
          val/<class>/
          test/<class>/

    Và oversample lớp ít trong train bằng cách copy file vật lý.
    """
    if not os.path.isdir(src_root):
        raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu nguồn: {src_root}")

    print(f"Đọc dataset từ: {src_root}")
    base_dataset = datasets.ImageFolder(root=src_root)

    print("classes:", base_dataset.classes)
    print("class_to_idx:", base_dataset.class_to_idx)

    targets = base_dataset.targets
    class_counts = Counter(targets)
    print("Tổng số mẫu theo lớp:", class_counts)

    # Chia stratified train/val/test
    train_indices, val_indices, test_indices = stratified_split_indices(
        targets,
        val_split=val_split,
        test_split=test_split,
        seed=seed,
    )

    split_indices = {
        "train": train_indices,
        "val": val_indices,
        "test": test_indices,
    }

    print(
        f"Số mẫu sau chia - train: {len(train_indices)}, "
        f"val: {len(val_indices)}, test: {len(test_indices)}"
    )

    # Xóa thư mục out_root cũ nếu tồn tại (cẩn thận)
    if os.path.isdir(out_root):
        print(f"CẢNH BÁO: Xóa toàn bộ thư mục đích cũ: {out_root}")
        shutil.rmtree(out_root)

    # Tạo cấu trúc và copy file (kèm oversample train)
    build_split_dirs(
        base_dataset=base_dataset,
        split_indices=split_indices,
        out_root=out_root,
        oversample_train=True,
    )

    print("Hoàn tất tạo dataset cho Ultralytics.")
    print(f"Cấu trúc mới nằm tại: {out_root}")


def prepare_balanced_dataset_for_roboflow(
    src_root: str,
    out_root: str,
) -> None:
    """
    Từ dataset gốc dạng:
        src_root/
          Early_blight/
          Bacterial_spot/
          Yellow_Leaf_Curl_Virus/

    Tạo dataset mới đã oversample cân bằng:
        out_root/
          Early_blight/
          Bacterial_spot/
          Yellow_Leaf_Curl_Virus/

    -> Dùng để upload lên Roboflow (Roboflow sẽ tự chia train/val/test).
    """
    if not os.path.isdir(src_root):
        raise FileNotFoundError(f"Không tìm thấy thư mục dữ liệu nguồn: {src_root}")

    print(f"Đọc dataset từ: {src_root}")
    base_dataset = datasets.ImageFolder(root=src_root)

    print("classes:", base_dataset.classes)
    print("class_to_idx:", base_dataset.class_to_idx)

    targets = base_dataset.targets
    class_counts = Counter(targets)
    print("Tổng số mẫu theo lớp (gốc):", class_counts)

    # Map class_idx -> danh sách chỉ số sample thuộc lớp đó
    class_to_indices: Dict[int, List[int]] = {}
    for idx, (_, label) in enumerate(base_dataset.samples):
        class_to_indices.setdefault(label, []).append(idx)

    # Tính target = số lượng lớn nhất trong các lớp
    max_count = max(len(idxs) for idxs in class_to_indices.values())
    print("Target mỗi lớp (max_count):", max_count)

    # Nếu thư mục đích đã tồn tại thì xóa để tránh lẫn file cũ
    if os.path.isdir(out_root):
        print(f"CẢNH BÁO: Xóa toàn bộ thư mục đích cũ: {out_root}")
        shutil.rmtree(out_root)

    for class_idx, idxs in class_to_indices.items():
        class_name = base_dataset.classes[class_idx]
        dst_dir = os.path.join(out_root, class_name)
        ensure_dir(dst_dir)

        # Copy toàn bộ file gốc
        for idx in idxs:
            src_path, _ = base_dataset.samples[idx]
            filename = os.path.basename(src_path)
            dst_path = os.path.join(dst_dir, filename)
            copy_file(src_path, dst_path)

        n_current = len(idxs)
        n_extra = max_count - n_current
        print(f"Lớp {class_name}: hiện có {n_current}, cần thêm {n_extra}")

        if n_current == 0 or n_extra <= 0:
            continue

        # Oversample: copy lặp lại file cho tới khi đạt ~max_count
        extra_copies = 0
        round_idx = 0
        while extra_copies < n_extra:
            base_idx = idxs[round_idx % n_current]
            src_path, _ = base_dataset.samples[base_idx]
            stem, ext = os.path.splitext(os.path.basename(src_path))
            new_filename = f"{stem}_copy{extra_copies + 1}{ext}"
            dst_path = os.path.join(dst_dir, new_filename)
            copy_file(src_path, dst_path)

            extra_copies += 1
            round_idx += 1

    print("Hoàn tất tạo dataset cân bằng cho Roboflow.")
    print(f"Upload thư mục này lên Roboflow: {out_root}")


def _get_augmentation_transforms() -> transforms.Compose:
    """Augmentation đa dạng cho làm giàu dữ liệu (PIL in -> PIL out)."""
    return transforms.Compose([
        transforms.RandomApply([
            transforms.RandomRotation(degrees=25),
        ], p=0.8),
        transforms.RandomApply([
            transforms.RandomResizedCrop(256, scale=(0.85, 1.0), ratio=(0.9, 1.1)),
        ], p=0.5),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomApply([
            transforms.ColorJitter(brightness=0.35, contrast=0.35, saturation=0.35, hue=0.12),
        ], p=0.7),
        transforms.RandomApply([
            transforms.GaussianBlur(kernel_size=3),
        ], p=0.25),
    ])


def enrich_dataset_to_target(
    src_root: str,
    out_root: str,
    target_per_class: int = 6000,
    use_augmentation: bool = True,
    seed: Optional[int] = 42,
) -> None:
    """
    Làm giàu dữ liệu: mỗi lớp đạt đúng target_per_class ảnh (mặc định 6000).

    - src_root: dataset gốc (Early_blight/, Bacterial_spot/, Yellow_Leaf_Curl_Virus/)
    - out_root: thư mục đích (cùng cấu trúc, mỗi lớp đủ target_per_class ảnh)
    - use_augmentation: True = tạo thêm ảnh bằng augmentation (xoay, lật, màu, blur...);
      False = chỉ copy lặp file gốc (nhanh nhưng ít đa dạng)
    """
    if seed is not None:
        random.seed(seed)

    if not os.path.isdir(src_root):
        raise FileNotFoundError(f"Không tìm thấy thư mục nguồn: {src_root}")

    base_dataset = datasets.ImageFolder(root=src_root)
    class_to_indices: Dict[int, List[int]] = {}
    for idx, (_, label) in enumerate(base_dataset.samples):
        class_to_indices.setdefault(label, []).append(idx)

    if os.path.isdir(out_root):
        print(f"CẢNH BÁO: Xóa thư mục đích cũ: {out_root}")
        shutil.rmtree(out_root)

    aug_transform = _get_augmentation_transforms() if use_augmentation else None

    for class_idx, idxs in class_to_indices.items():
        class_name = base_dataset.classes[class_idx]
        dst_dir = os.path.join(out_root, class_name)
        ensure_dir(dst_dir)

        n_current = len(idxs)
        n_needed = target_per_class - n_current
        print(f"Lớp {class_name}: gốc {n_current}, cần thêm {n_needed} để đạt {target_per_class}.")

        # 1) Copy toàn bộ ảnh gốc
        for idx in idxs:
            src_path, _ = base_dataset.samples[idx]
            name = os.path.basename(src_path)
            copy_file(src_path, os.path.join(dst_dir, name))

        if n_needed <= 0:
            continue

        # 2) Tạo thêm ảnh: augmentation hoặc copy
        if aug_transform is not None:
            added = 0
            attempt = 0
            while added < n_needed:
                idx = idxs[attempt % n_current]
                src_path, _ = base_dataset.samples[idx]
                try:
                    img = Image.open(src_path).convert("RGB")
                except Exception as e:
                    attempt += 1
                    continue
                aug_img = aug_transform(img)
                stem, ext = os.path.splitext(os.path.basename(src_path))
                new_name = f"{stem}_aug{added + 1}{ext}"
                out_path = os.path.join(dst_dir, new_name)
                aug_img.save(out_path, quality=95)
                added += 1
                attempt += 1
            print(f"  -> Đã tạo thêm {added} ảnh (augmentation).")
        else:
            added = 0
            while added < n_needed:
                idx = idxs[added % n_current]
                src_path, _ = base_dataset.samples[idx]
                stem, ext = os.path.splitext(os.path.basename(src_path))
                new_name = f"{stem}_copy{added + 1}{ext}"
                copy_file(src_path, os.path.join(dst_dir, new_name))
                added += 1
            print(f"  -> Đã copy thêm {added} ảnh (không augmentation).")

    print("Hoàn tất làm giàu dataset.")
    print(f"Kết quả tại: {out_root} (mỗi lớp ~{target_per_class} ảnh).")


def prepare_detection_dataset_from_classification(
    src_root: str,
    out_root: str,
    val_split: float = 0.15,
    test_split: float = 0.15,
    seed: Optional[int] = 42,
    full_image_bbox: bool = True,
) -> None:
    """
    Tạo cấu trúc dataset object detection (YOLO) từ dataset classification hiện có.

    Cấu trúc ra:
        out_root/
          train/images/   (ảnh gộp từ mọi lớp)
          train/labels/   (.txt mỗi ảnh, định dạng YOLO: class_id x_center y_center width height)
          valid/images/
          valid/labels/
          test/images/
          test/labels/

    - full_image_bbox: True = mỗi ảnh 1 box phủ toàn ảnh (class_id 0.5 0.5 1 1), dùng tạm khi chưa có bbox thật.
      Sau khi có bbox thật (ví dụ từ Roboflow), thay thế nội dung file .txt trong labels/.
    """
    if seed is not None:
        random.seed(seed)

    if not os.path.isdir(src_root):
        raise FileNotFoundError(f"Không tìm thấy thư mục nguồn: {src_root}")

    base_dataset = datasets.ImageFolder(root=src_root)
    targets = base_dataset.targets
    train_idx, val_idx, test_idx = stratified_split_indices(
        targets, val_split=val_split, test_split=test_split, seed=seed
    )

    splits = {"train": train_idx, "valid": val_idx, "test": test_idx}
    if os.path.isdir(out_root):
        print(f"CẢNH BÁO: Xóa thư mục đích cũ: {out_root}")
        shutil.rmtree(out_root)

    for split_name, indices in splits.items():
        im_dir = os.path.join(out_root, split_name, "images")
        lb_dir = os.path.join(out_root, split_name, "labels")
        ensure_dir(im_dir)
        ensure_dir(lb_dir)

        for i, idx in enumerate(indices):
            src_path, label = base_dataset.samples[idx]
            class_name = base_dataset.classes[label]
            stem, ext = os.path.splitext(os.path.basename(src_path))
            # Tên file: không khoảng trắng, đuôi ảnh lowercase (.jpg) để Hub/ Linux tìm được
            safe_stem = f"{class_name}_{i}_{stem}".replace(" ", "_")
            ext_lower = ext.lower() if ext else ".jpg"
            img_name = safe_stem + ext_lower
            lbl_name = safe_stem + ".txt"

            dst_img = os.path.join(im_dir, img_name)
            dst_lbl = os.path.join(lb_dir, lbl_name)
            copy_file(src_path, dst_img)

            if full_image_bbox:
                # YOLO: class_id x_center y_center width height (normalized 0-1), box toàn ảnh
                with open(dst_lbl, "w") as f:
                    f.write(f"{label} 0.5 0.5 1.0 1.0\n")

        print(f"{split_name}: {len(indices)} ảnh -> {im_dir}, {lb_dir}")

    print("Hoàn tất tạo dataset detection (YOLO).")
    print(f"Kết quả tại: {out_root}. Trỏ tomato_leaf.yaml vào thư mục này.")
    if full_image_bbox:
        print("Hiện dùng full-image bbox. Khi có bbox thật (Roboflow), thay file trong */labels/.")


def validate_detection_dataset(
    root_path: str,
    nc: int = 3,
) -> bool:
    """
    Kiểm tra dataset detection (YOLO) trước khi upload lên Hub.
    - Cấu trúc: root_path/train|valid|test/images và .../labels
    - Mỗi ảnh có file label cùng tên (stem), định dạng YOLO.
    Trả về True nếu hợp lệ, in ra lỗi và trả về False nếu có sai sót.
    """
    IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".JPG", ".JPEG", ".PNG"}
    splits = ["train", "valid", "test"]
    ok = True

    if not os.path.isdir(root_path):
        print(f"[LỖI] Không tìm thấy thư mục: {root_path}")
        return False

    for split in splits:
        im_dir = os.path.join(root_path, split, "images")
        lb_dir = os.path.join(root_path, split, "labels")

        if not os.path.isdir(im_dir):
            print(f"[LỖI] Thiếu thư mục: {im_dir}")
            ok = False
            continue
        if not os.path.isdir(lb_dir):
            print(f"[LỖI] Thiếu thư mục: {lb_dir}")
            ok = False
            continue

        def get_stems(dirpath: str, exts: Optional[set] = None) -> dict:
            out = {}
            for f in os.listdir(dirpath):
                p = os.path.join(dirpath, f)
                if not os.path.isfile(p):
                    continue
                stem, ext = os.path.splitext(f)
                if exts is not None and ext not in exts:
                    continue
                out[stem] = f
            return out

        images = get_stems(im_dir, IMG_EXTS)
        labels = get_stems(lb_dir, {".txt"})

        im_stems = set(images.keys())
        lb_stems = set(labels.keys())

        missing_label = im_stems - lb_stems
        missing_image = lb_stems - im_stems

        if missing_label:
            print(f"[{split}] Ảnh không có label ({len(missing_label)}): {list(missing_label)[:5]}{'...' if len(missing_label) > 5 else ''}")
            ok = False
        if missing_image:
            print(f"[{split}] Label không có ảnh ({len(missing_image)}): {list(missing_image)[:5]}{'...' if len(missing_image) > 5 else ''}")
            ok = False

        # Kiểm tra nội dung label (YOLO: class_id x_center y_center width height)
        for stem in lb_stems:
            lbl_path = os.path.join(lb_dir, labels[stem])
            try:
                with open(lbl_path, "r") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split()
                        if len(parts) != 5:
                            print(f"[{split}] {labels[stem]} dòng {line_num}: cần 5 số, có {len(parts)}")
                            ok = False
                            continue
                        try:
                            vals = [float(x) for x in parts]
                            cid = int(vals[0])
                            if cid < 0 or cid >= nc:
                                print(f"[{split}] {labels[stem]} dòng {line_num}: class_id={cid} ngoài [0,{nc-1}]")
                                ok = False
                            if not all(0 <= v <= 1 for v in vals[1:]):
                                print(f"[{split}] {labels[stem]} dòng {line_num}: x,y,w,h phải trong [0,1]")
                                ok = False
                        except ValueError:
                            print(f"[{split}] {labels[stem]} dòng {line_num}: không phải số")
                            ok = False
            except Exception as e:
                print(f"[{split}] Đọc label {labels[stem]}: {e}")
                ok = False

        if not missing_label and not missing_image:
            print(f"[{split}] OK: {len(im_stems)} ảnh, {len(lb_stems)} label.")

    if ok:
        print("Dataset hợp lệ. Có thể zip và upload lên Hub.")
    else:
        print("Dataset có lỗi. Sửa theo gợi ý trên rồi chạy lại kiểm tra.")
    return ok


def enrich_and_export_to_hub(
    src_root: str,
    out_root: str,
    target_per_class: int = 6000,
    val_split: float = 0.15,
    test_split: float = 0.15,
    use_augmentation: bool = True,
    seed: Optional[int] = 42,
    nc: int = 3,
    names: Optional[List[str]] = None,
) -> None:
    """
    Làm giàu lên target_per_class ảnh/lớp (mặc định 6000 → tổng 18000), ghi trực tiếp
    vào out_root (dataset_detection_hub) theo cấu trúc Hub: images/train|val|test,
    labels/train|val|test, data.yaml. Không tạo folder trung gian.
    """
    if names is None:
        names = ["Early_blight", "Bacterial_spot", "Yellow_Leaf_Curl_Virus"]
    if seed is not None:
        random.seed(seed)

    if not os.path.isdir(src_root):
        raise FileNotFoundError(f"Không tìm thấy thư mục nguồn: {src_root}")

    base_dataset = datasets.ImageFolder(root=src_root)
    class_to_indices: Dict[int, List[int]] = {}
    for idx, (_, label) in enumerate(base_dataset.samples):
        class_to_indices.setdefault(label, []).append(idx)

    aug_transform = _get_augmentation_transforms() if use_augmentation else None

    # Mỗi lớp: target_per_class item (class_idx, src_idx, aug_id). aug_id=0 = copy gốc, aug_id>0 = bản aug
    items_by_class: Dict[int, List[tuple]] = {}
    for class_idx, idxs in class_to_indices.items():
        n_orig = len(idxs)
        items = [(class_idx, idxs[i], 0) for i in range(n_orig)]
        for j in range(target_per_class - n_orig):
            items.append((class_idx, idxs[j % n_orig], j + 1))
        random.shuffle(items)
        items_by_class[class_idx] = items[:target_per_class]
        n_aug = max(0, target_per_class - n_orig)
        print(f"Lớp {base_dataset.classes[class_idx]}: {target_per_class} ảnh (gốc {n_orig}, aug {n_aug})")

    # Stratified split: mỗi lớp chia train/val/test
    split_names = ["train", "val", "test"]
    n_val = int(target_per_class * val_split)
    n_test = int(target_per_class * test_split)
    n_train = target_per_class - n_val - n_test
    split_sizes = [n_train, n_val, n_test]

    if os.path.isdir(out_root):
        print(f"Xóa thư mục đích cũ: {out_root}")
        shutil.rmtree(out_root)

    for hub_split in split_names:
        ensure_dir(os.path.join(out_root, "images", hub_split))
        ensure_dir(os.path.join(out_root, "labels", hub_split))

    written = {s: 0 for s in split_names}
    for class_idx, items in items_by_class.items():
        random.shuffle(items)
        off = 0
        for si, split_name in enumerate(split_names):
            size = split_sizes[si]
            chunk = items[off : off + size]
            off += size
            for i, (cidx, src_idx, aug_id) in enumerate(chunk):
                src_path, _ = base_dataset.samples[src_idx]
                stem = f"{names[cidx]}_{split_name}_{written[split_name]:06d}"
                stem = stem.replace(" ", "_")
                img_path = os.path.join(out_root, "images", split_name, stem + ".jpg")
                lbl_path = os.path.join(out_root, "labels", split_name, stem + ".txt")
                ensure_dir(os.path.dirname(img_path))
                ensure_dir(os.path.dirname(lbl_path))
                if aug_id == 0:
                    copy_file(src_path, img_path)
                else:
                    try:
                        img = Image.open(src_path).convert("RGB")
                        aug_img = aug_transform(img)
                        aug_img.save(img_path, quality=95)
                    except Exception:
                        copy_file(src_path, img_path)
                with open(lbl_path, "w") as f:
                    f.write(f"{cidx} 0.5 0.5 1.0 1.0\n")
                written[split_name] += 1
        print(f"  -> Đã ghi {sum(split_sizes)} ảnh cho lớp {base_dataset.classes[class_idx]}.")

    yaml_path = os.path.join(out_root, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"""# Dataset cho Ultralytics Hub (object detection) — {target_per_class * nc} ảnh
path: .
train: images/train
val: images/val
test: images/test

nc: {nc}
names: {names}
""")
    print(f"Đã tạo {yaml_path}. Tổng: train {written['train']}, val {written['val']}, test {written['test']}.")
    print("Nén thư mục này thành zip rồi upload lên Hub.")


def export_dataset_for_ultralytics_hub(
    src_root: str,
    out_root: str,
    nc: int = 3,
    names: Optional[List[str]] = None,
) -> None:
    """
    Chuyển dataset từ cấu trúc (train/images, train/labels, valid/..., test/...)
    sang đúng cấu trúc Ultralytics Hub cần:
        out_root/
          images/train/   images/val/   images/test/
          labels/train/   labels/val/   labels/test/
          data.yaml
    Hub yêu cầu: path: ., train: images/train, val: images/val (không dùng "valid").
    Sau khi chạy, zip thư mục out_root và upload file zip lên Hub.
    """
    if names is None:
        names = ["Early_blight", "Bacterial_spot", "Yellow_Leaf_Curl_Virus"]

    split_map = {"train": "train", "valid": "val", "test": "test"}

    if os.path.isdir(out_root):
        print(f"Xóa thư mục đích cũ: {out_root}")
        shutil.rmtree(out_root)

    for src_split, hub_split in split_map.items():
        src_im = os.path.join(src_root, src_split, "images")
        src_lb = os.path.join(src_root, src_split, "labels")
        dst_im = os.path.join(out_root, "images", hub_split)
        dst_lb = os.path.join(out_root, "labels", hub_split)
        if not os.path.isdir(src_im) or not os.path.isdir(src_lb):
            continue
        ensure_dir(dst_im)
        ensure_dir(dst_lb)
        for f in os.listdir(src_im):
            if not os.path.isfile(os.path.join(src_im, f)):
                continue
            copy_file(os.path.join(src_im, f), os.path.join(dst_im, f))
        for f in os.listdir(src_lb):
            if not os.path.isfile(os.path.join(src_lb, f)):
                continue
            copy_file(os.path.join(src_lb, f), os.path.join(dst_lb, f))
        print(f"Đã copy {src_split} -> images/{hub_split}, labels/{hub_split}")

    yaml_path = os.path.join(out_root, "data.yaml")
    yaml_content = f"""# Dataset cho Ultralytics Hub (object detection)
path: .
train: images/train
val: images/val
test: images/test

nc: {nc}
names: {names}
"""
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"Đã tạo {yaml_path}")
    print("Bước tiếp: nén thư mục này thành zip (trong zip phải có images/, labels/, data.yaml) rồi upload lên Hub.")


if __name__ == "__main__":
    # CHẾ ĐỘ CHẠY:
    # - "enrich_hub": làm giàu 6000 ảnh/lớp (18k) và ghi trực tiếp vào dataset_detection_hub (không tạo folder mới)
    # - "export_hub": tạo dataset_detection_hub từ dataset_detection (cấu trúc Hub)
    # - "check": kiểm tra dataset detection
    # - "enrich_6000": làm giàu mỗi lớp 6000 ảnh -> dataset_enriched_6000
    # - "roboflow_balanced": dataset cân bằng để upload Roboflow
    # - "ultralytics_splits": train/val/test classification
    # - "detection": cấu trúc detection -> dataset_detection
    MODE = "enrich_hub"

    SRC_ROOT = r"D:\BkStar\TomatoLeaf\dataset"
    DETECTION_ROOT = r"D:\BkStar\TomatoLeaf\dataset_detection"
    HUB_EXPORT_ROOT = r"D:\BkStar\TomatoLeaf\dataset_detection_hub"

    if MODE == "enrich_hub":
        enrich_and_export_to_hub(
            src_root=SRC_ROOT,
            out_root=HUB_EXPORT_ROOT,
            target_per_class=6000,
            val_split=0.15,
            test_split=0.15,
            use_augmentation=True,
            seed=42,
            nc=3,
            names=["Early_blight", "Bacterial_spot", "Yellow_Leaf_Curl_Virus"],
        )

    elif MODE == "export_hub":
        export_dataset_for_ultralytics_hub(
            src_root=DETECTION_ROOT,
            out_root=HUB_EXPORT_ROOT,
            nc=3,
            names=["Early_blight", "Bacterial_spot", "Yellow_Leaf_Curl_Virus"],
        )

    elif MODE == "check":
        validate_detection_dataset(root_path=DETECTION_ROOT, nc=3)

    elif MODE == "enrich_6000":
        OUT_ROOT = r"D:\BkStar\TomatoLeaf\dataset_enriched_6000"
        enrich_dataset_to_target(
            src_root=SRC_ROOT,
            out_root=OUT_ROOT,
            target_per_class=6000,
            use_augmentation=True,  # True = augmentation (hiệu quả), False = chỉ copy
            seed=42,
        )

    elif MODE == "roboflow_balanced":
        OUT_ROOT = r"D:\BkStar\TomatoLeaf\dataset_balanced"
        prepare_balanced_dataset_for_roboflow(
            src_root=SRC_ROOT,
            out_root=OUT_ROOT,
        )

    elif MODE == "ultralytics_splits":
        OUT_ROOT = r"D:\BkStar\TomatoLeaf\ultralytics_cls"
        prepare_ultralytics_classification_dataset(
            src_root=SRC_ROOT,
            out_root=OUT_ROOT,
            val_split=0.15,
            test_split=0.15,
            seed=42,
        )

    elif MODE == "detection":
        OUT_ROOT = r"D:\BkStar\TomatoLeaf\dataset_detection"
        prepare_detection_dataset_from_classification(
            src_root=SRC_ROOT,
            out_root=OUT_ROOT,
            val_split=0.15,
            test_split=0.15,
            seed=42,
            full_image_bbox=True,  # tạm 1 box/ảnh; thay bằng bbox thật từ Roboflow sau
        )


