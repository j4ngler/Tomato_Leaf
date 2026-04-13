"""
Huấn luyện tuần tự nhiều phiên bản YOLO (Ultralytics) trên cùng dataset và ghi bảng so sánh.

Ví dụ:
  python train_yolo_compare.py
  python train_yolo_compare.py --epochs 10 --batch 8
  python train_yolo_compare.py --models yolov9s.pt yolo11s.pt
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ultralytics import YOLO

# Mặc định: chỉ YOLOv9 vs YOLO11 (bản nhẹ: v9 không có "n", dùng t ≈ tiny; v11 dùng nano).
DEFAULT_MODELS = [
    "yolov9t.pt",
    "yolo11n.pt",
]


def _metrics_from_trainer(model: YOLO) -> dict[str, float] | None:
    m = getattr(model, "metrics", None)
    if m is None or not hasattr(m, "results_dict"):
        return None
    # Ultralytics: results_dict là @property (dict), không phải hàm — gọi () sẽ lỗi.
    rd = m.results_dict
    raw = rd() if callable(rd) else rd
    return {
        "precision": float(raw.get("metrics/precision(B)", 0.0)),
        "recall": float(raw.get("metrics/recall(B)", 0.0)),
        "mAP50": float(raw.get("metrics/mAP50(B)", 0.0)),
        "mAP50-95": float(raw.get("metrics/mAP50-95(B)", 0.0)),
        "fitness": float(raw.get("fitness", 0.0)),
    }


def _metrics_from_results_csv(csv_path: Path) -> dict[str, float] | None:
    if not csv_path.is_file():
        return None
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    last = rows[-1]
    try:
        map5095 = float(last["metrics/mAP50-95(B)"])
        return {
            "precision": float(last["metrics/precision(B)"]),
            "recall": float(last["metrics/recall(B)"]),
            "mAP50": float(last["metrics/mAP50(B)"]),
            "mAP50-95": map5095,
            "fitness": map5095,
        }
    except (KeyError, ValueError):
        return None


def _collect_row(model_name: str, model: YOLO, save_dir: Path) -> dict[str, str | float]:
    row: dict[str, str | float] = {"model": model_name, "save_dir": str(save_dir)}
    metrics = _metrics_from_trainer(model)
    if metrics is None:
        metrics = _metrics_from_results_csv(save_dir / "results.csv")
    if metrics is None:
        row["error"] = "Không đọc được metric (trainer / results.csv)."
        return row
    row.update(metrics)
    return row


def main() -> None:
    root = Path(__file__).resolve().parent
    data_yaml = root / "dataset_detection_hub" / "data.yaml"

    parser = argparse.ArgumentParser(description="So sánh huấn luyện nhiều backbone YOLO (Ultralytics).")
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        metavar="WEIGHT",
        help="Danh sách file .pt (mặc định: bộ nano/tiny chuẩn).",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0", help="0, 0,1 hoặc cpu")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--project",
        default="tomato_yolo_compare",
        help="Thư mục con dưới runs/detect/",
    )
    parser.add_argument(
        "--summary",
        default="comparison_summary.csv",
        help="Tên file CSV tổng hợp (đặt trong runs/detect/<project>/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ in kế hoạch, không gọi train.",
    )
    args = parser.parse_args()

    models = args.models if args.models else DEFAULT_MODELS

    if not data_yaml.is_file():
        raise FileNotFoundError(f"Không thấy dataset: {data_yaml}")

    out_dir = root / "runs" / "detect" / args.project
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / args.summary

    print("Dataset:", data_yaml)
    print("Project:", args.project)
    print("Models:", models)
    if args.dry_run:
        print("Dry-run: bỏ qua huấn luyện.")
        return

    all_rows: list[dict[str, str | float]] = []

    for model_name in models:
        run_name = f"tomato_{Path(model_name).stem}"
        print(f"\n=== Train: {model_name} -> {run_name} ===")
        try:
            yolo = YOLO(model_name)
            yolo.train(
                data=str(data_yaml),
                epochs=args.epochs,
                imgsz=args.imgsz,
                batch=args.batch,
                device=args.device,
                project=args.project,
                name=run_name,
                workers=args.workers,
                exist_ok=True,
            )
            save_dir = Path(yolo.trainer.save_dir)
            row = _collect_row(model_name, yolo, save_dir)
        except Exception as e:  # noqa: BLE001 — gom lỗi từng model để chạy tiếp
            row = {
                "model": model_name,
                "save_dir": "",
                "error": str(e),
            }
            print(f"Lỗi: {e}")
        all_rows.append(row)

    fieldnames = ["model", "save_dir", "precision", "recall", "mAP50", "mAP50-95", "fitness", "error"]
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in all_rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"\nĐã ghi bảng so sánh: {summary_path}")
    for row in all_rows:
        err = row.get("error", "")
        if err:
            print(f"  {row['model']}: LỖI — {err}")
        else:
            print(
                f"  {row['model']}: P={row.get('precision', ''):.4f} "
                f"R={row.get('recall', ''):.4f} mAP50={row.get('mAP50', ''):.4f} "
                f"mAP50-95={row.get('mAP50-95', ''):.4f}"
            )


if __name__ == "__main__":
    main()
