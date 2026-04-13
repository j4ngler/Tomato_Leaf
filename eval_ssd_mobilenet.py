from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Dict, List

import torch
from torch.utils.data import DataLoader
from torchmetrics.detection.mean_ap import MeanAveragePrecision

from train_ssd_mobilenet import (
    YoloDetectionDataset,
    collate_fn,
    create_model,
    load_data_cfg,
    resolve_split_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate SSD MobileNet on YOLO-format dataset")
    parser.add_argument("--data", type=str, default="dataset_detection_hub/data.yaml", help="Path to data.yaml")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="runs_ssd_mobilenet/best_ssd_mobilenet.pt",
        help="Path to SSD checkpoint",
    )
    parser.add_argument("--split", type=str, default="val", choices=["train", "val", "test"], help="Eval split")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--workers", type=int, default=4, help="Num workers")
    parser.add_argument("--device", type=str, default="cuda", help="cuda or cpu")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold for predictions")
    parser.add_argument("--out", type=str, default="runs_ssd_mobilenet", help="Output folder")
    return parser.parse_args()


def resolve_dataset_root(root: Path, data_yaml: Path, cfg: Dict) -> Path:
    cfg_path = str(cfg.get("path", "."))
    if cfg_path in {"", "."}:
        return data_yaml.parent.resolve()

    candidate_from_yaml_parent = (data_yaml.parent / cfg_path).resolve()
    candidate_from_project_root = (root / cfg_path).resolve()

    if candidate_from_yaml_parent.exists():
        return candidate_from_yaml_parent
    if candidate_from_project_root.exists():
        return candidate_from_project_root
    return candidate_from_yaml_parent


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    data_yaml = (root / args.data).resolve()
    ckpt_path = (root / args.checkpoint).resolve()
    out_dir = (root / args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_data_cfg(data_yaml)
    dataset_root = resolve_dataset_root(root, data_yaml, cfg)

    split_to_images = {
        "train": cfg["train"],
        "val": cfg["val"],
        "test": cfg["test"],
    }
    split_to_labels = {
        "train": "train",
        "val": "val",
        "test": "test",
    }

    image_dir = resolve_split_dir(dataset_root, split_to_images[args.split])
    label_dir = (dataset_root / "labels" / split_to_labels[args.split]).resolve()
    if not image_dir.exists() or not label_dir.exists():
        raise FileNotFoundError(f"Split not found: {image_dir} | {label_dir}")

    num_classes = int(cfg["nc"]) + 1
    class_names = cfg.get("names", [])

    dataset = YoloDetectionDataset(image_dir=image_dir, label_dir=label_dir)
    loader = DataLoader(
        dataset,
        batch_size=args.batch,
        shuffle=False,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )

    device_str = "cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu"
    device = torch.device(device_str)

    model = create_model(num_classes=num_classes)
    checkpoint = torch.load(ckpt_path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model = model.to(device)
    model.eval()

    metric = MeanAveragePrecision(
        box_format="xyxy",
        class_metrics=True,
        backend="faster_coco_eval",
    ).to(device)
    total_infer_ms = 0.0
    total_images = 0

    with torch.no_grad():
        for images, targets in loader:
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            if device.type == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            outputs = model(images)
            if device.type == "cuda":
                torch.cuda.synchronize()
            t1 = time.perf_counter()

            infer_ms = (t1 - t0) * 1000.0
            total_infer_ms += infer_ms
            total_images += len(images)

            filtered_outputs: List[Dict[str, torch.Tensor]] = []
            for out in outputs:
                keep = out["scores"] >= args.conf
                filtered_outputs.append(
                    {
                        "boxes": out["boxes"][keep],
                        "scores": out["scores"][keep],
                        "labels": out["labels"][keep],
                    }
                )

            metric.update(filtered_outputs, targets)

    results = metric.compute()
    mean_infer_ms = total_infer_ms / max(total_images, 1)

    map_50 = float(results["map_50"].item())
    map_5095 = float(results["map"].item())
    mar_100 = float(results["mar_100"].item())

    # Precision gần đúng ở IoU 0.5 bằng mAP50 (một điểm báo cáo đơn giản)
    precision_approx = map_50
    recall_approx = mar_100

    print(f"Split: {args.split}")
    print(f"Images: {len(dataset)}")
    print(f"Device: {device}")
    print(f"mAP50: {map_50:.4f}")
    print(f"mAP50-95: {map_5095:.4f}")
    print(f"mAR@100: {mar_100:.4f}")
    print(f"Inference: {mean_infer_ms:.3f} ms/image (conf>={args.conf})")

    csv_path = out_dir / f"ssd_eval_{args.split}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "split",
                "images",
                "precision_approx",
                "recall_approx",
                "mAP50",
                "mAP50_95",
                "inference_ms_per_image",
                "best_val_loss",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "model": "SSD-MobileNetV3",
                "split": args.split,
                "images": len(dataset),
                "precision_approx": f"{precision_approx:.6f}",
                "recall_approx": f"{recall_approx:.6f}",
                "mAP50": f"{map_50:.6f}",
                "mAP50_95": f"{map_5095:.6f}",
                "inference_ms_per_image": f"{mean_infer_ms:.6f}",
                "best_val_loss": f"{checkpoint.get('val_loss', float('nan')):.6f}",
            }
        )

    print(f"Saved evaluation CSV: {csv_path}")


if __name__ == "__main__":
    main()

