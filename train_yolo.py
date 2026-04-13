from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    root = Path(__file__).resolve().parent

    # File cấu hình dataset detection (đã chuẩn cho Ultralytics / Hub)
    data_yaml = root / "dataset_detection_hub" / "data.yaml"

    # Model YOLO26 bản Nano (nhẹ, phù hợp thử nghiệm)
    model_name = "yolo26n.pt"

    model = YOLO(model_name)

    model.train(
        data=str(data_yaml),
        epochs=50,          # tăng/giảm tùy nhu cầu
        imgsz=640,
        batch=16,           # nếu thiếu VRAM có thể giảm xuống 8
        device=0,           # 0 = GPU đầu tiên, "cpu" nếu không có GPU
        project="runs_yolo26",
        name="tomato_yolo26n",
        workers=4,
    )


if __name__ == "__main__":
    main()

