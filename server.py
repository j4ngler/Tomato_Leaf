import io
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image
from ultralytics import YOLO


# Đường dẫn tới model YOLO đã train.
# Model trong thư mục dự án (best.pt) hoặc thư mục cha (../best.pt).
MODEL_PATH = "best.pt"

# Tên lớp theo đúng thứ tự khi train model
DEFAULT_CLASS_NAMES = ["Early_blight", "Bacterial_spot", "Yellow_Leaf_Curl_Virus"]


app = FastAPI(title="Tomato Leaf Disease Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev: cho phép mọi origin, sau này có thể siết lại
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend (PC + mobile) từ thư mục static/ tại /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    """Trả về trang index của frontend."""
    return FileResponse("static/index.html")


@app.on_event("startup")
def load_model() -> None:
    """Load YOLO model một lần khi server khởi động."""
    try:
        model = YOLO(MODEL_PATH)
    except Exception as e:
        raise RuntimeError(f"Không thể load model từ '{MODEL_PATH}': {e}") from e
    app.state.model = model
    app.state.class_names = (
        list(model.names.values())
        if getattr(model, "names", None)
        else DEFAULT_CLASS_NAMES
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _read_image(file_bytes: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không đọc được ảnh: {e}") from e
    return img


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict:
    """Nhận file ảnh, chạy YOLO, trả về danh sách bệnh phát hiện được."""
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Vui lòng upload file ảnh (jpg/png/webp...).")

    img_bytes = await file.read()
    img = _read_image(img_bytes)

    model: YOLO = app.state.model
    class_names: List[str] = app.state.class_names

    try:
        results = model(img)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi chạy mô hình: {e}") from e

    diseases = []
    for box in results.boxes:
        cls_id = int(box.cls.item())
        conf = float(box.conf.item())
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]

        name: Optional[str] = None
        if 0 <= cls_id < len(class_names):
            name = class_names[cls_id]

        diseases.append(
            {
                "class_id": cls_id,
                "name": name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
            }
        )

    return {
        "num_detections": len(diseases),
        "diseases": diseases,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

