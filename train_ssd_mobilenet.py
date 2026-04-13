from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import yaml
from PIL import Image
from torch import nn, optim
from torch.utils.data import DataLoader, Dataset
from torchvision.models import MobileNet_V3_Large_Weights
from torchvision.models.detection import ssdlite320_mobilenet_v3_large
from torchvision.transforms import functional as F


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SSD MobileNetV3 on YOLO-format dataset")
    parser.add_argument("--data", type=str, default="dataset_detection_hub/data.yaml", help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=30, help="Number of epochs")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--workers", type=int, default=4, help="Num workers")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--device", type=str, default="cuda", help="cuda or cpu")
    parser.add_argument("--out", type=str, default="runs_ssd_mobilenet", help="Output folder")
    return parser.parse_args()


def load_data_cfg(data_yaml: Path) -> Dict:
    with data_yaml.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_split_dir(dataset_root: Path, split_path: str) -> Path:
    # data.yaml thường có dạng images/train
    return (dataset_root / split_path).resolve()


class YoloDetectionDataset(Dataset):
    def __init__(self, image_dir: Path, label_dir: Path) -> None:
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.images = sorted(
            p for p in self.image_dir.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS
        )

    def __len__(self) -> int:
        return len(self.images)

    def _read_yolo_labels(self, label_path: Path, img_w: int, img_h: int) -> Tuple[torch.Tensor, torch.Tensor]:
        boxes: List[List[float]] = []
        labels: List[int] = []

        if label_path.exists():
            with label_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) != 5:
                        continue

                    cls_id, x_c, y_c, w, h = map(float, parts)
                    x_c *= img_w
                    y_c *= img_h
                    w *= img_w
                    h *= img_h

                    x1 = max(0.0, x_c - w / 2.0)
                    y1 = max(0.0, y_c - h / 2.0)
                    x2 = min(float(img_w), x_c + w / 2.0)
                    y2 = min(float(img_h), y_c + h / 2.0)

                    if x2 <= x1 or y2 <= y1:
                        continue

                    boxes.append([x1, y1, x2, y2])
                    # SSD dùng 0 cho background, nên nhãn thật bắt đầu từ 1
                    labels.append(int(cls_id) + 1)

        if boxes:
            box_tensor = torch.tensor(boxes, dtype=torch.float32)
            label_tensor = torch.tensor(labels, dtype=torch.int64)
        else:
            box_tensor = torch.zeros((0, 4), dtype=torch.float32)
            label_tensor = torch.zeros((0,), dtype=torch.int64)

        return box_tensor, label_tensor

    def __getitem__(self, idx: int):
        img_path = self.images[idx]
        label_path = self.label_dir / f"{img_path.stem}.txt"

        image = Image.open(img_path).convert("RGB")
        img_w, img_h = image.size
        boxes, labels = self._read_yolo_labels(label_path, img_w, img_h)

        target = {
            "boxes": boxes,
            "labels": labels,
            "image_id": torch.tensor([idx], dtype=torch.int64),
            "area": ((boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])) if boxes.numel() else torch.zeros((0,), dtype=torch.float32),
            "iscrowd": torch.zeros((labels.shape[0],), dtype=torch.int64),
        }

        image = F.to_tensor(image)
        return image, target


def collate_fn(batch):
    return tuple(zip(*batch))


def create_model(num_classes: int) -> nn.Module:
    model = ssdlite320_mobilenet_v3_large(
        # Không dùng detection head pretrain COCO (91 classes),
        # chỉ dùng backbone pretrain để train num_classes tùy chỉnh.
        weights=None,
        weights_backbone=MobileNet_V3_Large_Weights.DEFAULT,
        num_classes=num_classes,
    )
    return model


def run_epoch(model: nn.Module, loader: DataLoader, device: torch.device, optimizer=None) -> float:
    is_train = optimizer is not None
    model.train()

    total_loss = 0.0
    total_batches = 0

    for images, targets in loader:
        images = [img.to(device) for img in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        with torch.set_grad_enabled(is_train):
            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())

            if is_train:
                optimizer.zero_grad(set_to_none=True)
                losses.backward()
                optimizer.step()

        total_loss += losses.item()
        total_batches += 1

    return total_loss / max(total_batches, 1)


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    data_yaml = (root / args.data).resolve()

    cfg = load_data_cfg(data_yaml)
    cfg_path = str(cfg.get("path", "."))
    # Hỗ trợ cả 2 kiểu data.yaml:
    # - path: .
    # - path: dataset_detection_hub
    if cfg_path in {"", "."}:
        dataset_root = data_yaml.parent.resolve()
    else:
        candidate_from_yaml_parent = (data_yaml.parent / cfg_path).resolve()
        candidate_from_project_root = (root / cfg_path).resolve()
        if candidate_from_yaml_parent.exists():
            dataset_root = candidate_from_yaml_parent
        elif candidate_from_project_root.exists():
            dataset_root = candidate_from_project_root
        else:
            dataset_root = candidate_from_yaml_parent

    train_image_dir = resolve_split_dir(dataset_root, cfg["train"])
    val_image_dir = resolve_split_dir(dataset_root, cfg["val"])
    train_label_dir = (dataset_root / "labels" / "train").resolve()
    val_label_dir = (dataset_root / "labels" / "val").resolve()

    class_names = cfg.get("names", [])
    num_classes = int(cfg["nc"]) + 1  # +1 cho background class

    if not train_image_dir.exists() or not train_label_dir.exists():
        raise FileNotFoundError(f"Train data not found: {train_image_dir} | {train_label_dir}")
    if not val_image_dir.exists() or not val_label_dir.exists():
        raise FileNotFoundError(f"Val data not found: {val_image_dir} | {val_label_dir}")

    train_ds = YoloDetectionDataset(train_image_dir, train_label_dir)
    val_ds = YoloDetectionDataset(val_image_dir, val_label_dir)

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch,
        shuffle=True,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch,
        shuffle=False,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )

    device_str = "cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    device = torch.device(device_str)

    model = create_model(num_classes=num_classes).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr)

    out_dir = (root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    best_path = out_dir / "best_ssd_mobilenet.pt"
    last_path = out_dir / "last_ssd_mobilenet.pt"

    best_val = float("inf")
    print(f"Device: {device}")
    print(f"Classes ({len(class_names)}): {class_names}")
    print(f"Train images: {len(train_ds)} | Val images: {len(val_ds)}")

    for epoch in range(1, args.epochs + 1):
        train_loss = run_epoch(model, train_loader, device, optimizer=optimizer)
        with torch.no_grad():
            val_loss = run_epoch(model, val_loader, device, optimizer=None)

        print(f"[Epoch {epoch:03d}/{args.epochs}] train_loss={train_loss:.4f} | val_loss={val_loss:.4f}")

        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "train_loss": train_loss,
                "val_loss": val_loss,
                "class_names": class_names,
            },
            last_path,
        )

        if val_loss < best_val:
            best_val = val_loss
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "class_names": class_names,
                },
                best_path,
            )
            print(f"  -> Saved best model: {best_path}")

    print(f"Done. Best val_loss={best_val:.4f}")
    print(f"Best checkpoint: {best_path}")
    print(f"Last checkpoint: {last_path}")


if __name__ == "__main__":
    main()

