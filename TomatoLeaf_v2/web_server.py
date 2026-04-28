import io
import os
import random
import threading
import time
import base64
import sys
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parent
WEB_UI_DIR = ROOT_DIR / "web_ui"
DATASET_DIR = ROOT_DIR.parent / "dataset_detection"
PROJECT_ROOT = ROOT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_dotenv_if_present(path: Path) -> None:
    """Đọc file .env dạng KEY=VALUE (không ghi đè biến môi trường đã set sẵn)."""
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        k = key.strip()
        v = rest.strip()
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        if k:
            os.environ.setdefault(k, v)


_load_dotenv_if_present(ROOT_DIR / ".env")

CLASS_NAMES = {
    0: "Early blight",
    1: "Bacterial spot",
    2: "Yellow Leaf Curl Virus",
}


@dataclass
class FrameItem:
    split: str
    image_path: Path
    label_path: Path


class ModePayload(BaseModel):
    manual: bool


class DevicePayload(BaseModel):
    device: str
    state: bool


class PtzPayload(BaseModel):
    action: str


class CaptureBurstPayload(BaseModel):
    count: int = Field(default=5, ge=1, le=30)
    interval_sec: float = Field(default=3.0, ge=0.5, le=60.0)
    source: str = "rtsp"  # rtsp | dataset
    split: str = "train"  # chỉ dùng cho dataset


class CaptureSchedulePayload(BaseModel):
    run_at: str
    count: int = Field(default=5, ge=1, le=30)
    interval_sec: float = Field(default=3.0, ge=0.5, le=60.0)
    source: str = "rtsp"  # rtsp | dataset
    split: str = "train"  # chỉ dùng cho dataset


class AppState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.items_by_split: dict[str, list[FrameItem]] = {"train": [], "valid": [], "test": []}
        self.frame_idx_by_split: dict[str, int] = {"train": 0, "valid": 0, "test": 0}
        self.logs: deque[dict[str, str]] = deque(maxlen=200)
        self.manual = True
        self.devices = {
            "pump": False,
            "fan-cool": False,
            "fan-dehum": False,
            "light": False,
        }
        self.sensor = {
            "temperature": 30.9,
            "humidity": 56.3,
            "light": 195.8,
            "soil": 23.0,
        }
        self.ptz_client = None
        self.capture_dir = ROOT_DIR / "captures"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.schedule_lock = threading.Lock()
        self.schedule_job: dict[str, Any] | None = None

    def log(self, message: str) -> None:
        self.logs.appendleft(
            {"time": datetime.now().strftime("%H:%M:%S"), "message": message}
        )


state = AppState()
app = FastAPI(title="TomatoLeaf v2 Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(WEB_UI_DIR)), name="static")


def _resolve_vi_font(size: int = 18) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Ưu tiên font có hỗ trợ tiếng Việt để vẽ nhãn bbox có dấu."""
    font_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    for fp in font_candidates:
        try:
            if fp.exists():
                return ImageFont.truetype(str(fp), size=size)
        except Exception:
            continue
    return ImageFont.load_default()


VI_FONT = _resolve_vi_font(18)

try:
    import cv2

    CV2_AVAILABLE = True
except Exception:
    cv2 = None  # type: ignore[misc, assignment]
    CV2_AVAILABLE = False

try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
    YOLO_IMPORT_ERROR = ""
except Exception:
    YOLO = None  # type: ignore[assignment]
    YOLO_AVAILABLE = False
    YOLO_IMPORT_ERROR = str(sys.exc_info()[1] or "unknown import error")


def _jpeg_placeholder_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (640, 360), (30, 41, 59)).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _resolve_rtsp_url() -> str:
    """Giống camera_control/test_rtsp.py & schedule_* — có thể override bằng CAM_RTSP_URL."""
    direct = (
        (os.getenv("CAM_RTSP_URL") or os.getenv("RTSP_URL") or "").strip()
    )
    if direct:
        return direct
    user = os.getenv("RTSP_USER", os.getenv("CAM_USER", "admin"))
    pwd = (
        os.getenv("RTSP_PASS")
        or os.getenv("CAM_RTSP_PASS")
        or os.getenv("CAM_PASS")
        or ""
    ).strip()
    host = os.getenv("RTSP_HOST", "192.168.1.57").strip()
    port = os.getenv("RTSP_PORT", "554").strip()
    path = os.getenv(
        "RTSP_PATH", "/cam/realmonitor?channel=1&subtype=0"
    ).strip()
    if not path.startswith("/"):
        path = "/" + path
    if not pwd:
        return ""
    return f"rtsp://{user}:{quote(pwd, safe='')}@{host}:{port}{path}"


class RtspStreamManager:
    """Đọc RTSP bằng OpenCV, phát MJPEG qua HTTP cho trình duyệt."""

    def __init__(self) -> None:
        self.url = _resolve_rtsp_url().strip()
        self.lock = threading.Lock()
        self._placeholder = _jpeg_placeholder_bytes()
        self.last_jpeg: bytes = self._placeholder
        self.has_live_frame = False
        self.error: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.url and CV2_AVAILABLE)

    @staticmethod
    def _mask_url(url: str) -> str:
        if "@" in url:
            return url.split("@", 1)[-1]
        return url

    def start(self) -> None:
        if not self.enabled:
            return
        self._thread = threading.Thread(target=self._run, name="rtsp-reader", daemon=True)
        self._thread.start()
        state.log(f"Đã bật đọc RTSP: {self._mask_url(self.url)}")

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=4.0)

    def _run(self) -> None:
        assert cv2 is not None
        backoff = 1.0
        while not self._stop.is_set():
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                with self.lock:
                    self.error = "Không mở được luồng RTSP."
                    self.has_live_frame = False
                time.sleep(min(backoff, 5.0))
                backoff = min(backoff * 1.5, 5.0)
                continue
            backoff = 1.0
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            with self.lock:
                self.error = None
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    with self.lock:
                        self.error = "Mất frame từ RTSP."
                        self.has_live_frame = False
                    break
                enc_ok, buf = cv2.imencode(
                    ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82]
                )
                if enc_ok:
                    with self.lock:
                        self.last_jpeg = buf.tobytes()
                        self.has_live_frame = True
                time.sleep(0.033)
            cap.release()
            time.sleep(0.5)


rtsp_stream = RtspStreamManager()


def _resolve_detector_checkpoint() -> Path:
    direct = (os.getenv("YOLO_MODEL_PATH") or os.getenv("DETECTOR_MODEL_PATH") or "").strip()
    if direct:
        p = Path(direct)
        if not p.is_absolute():
            p = (ROOT_DIR.parent / p).resolve()
        return p
    candidate_in_module = (ROOT_DIR / "models" / "best.pt").resolve()
    if candidate_in_module.exists():
        return candidate_in_module
    return (ROOT_DIR.parent / "best.pt").resolve()


class DetectionEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model = None
        self._class_names = list(CLASS_NAMES.values())
        self._loaded_ckpt: Path | None = None
        self._error: str | None = None

    @property
    def available(self) -> bool:
        return YOLO_AVAILABLE

    @property
    def error(self) -> str | None:
        return self._error

    def _load_if_needed(self) -> None:
        if self._model is not None:
            return
        if not YOLO_AVAILABLE or YOLO is None:
            self._error = (
                "Thiếu thư viện ultralytics để chạy YOLO."
                + (f" ({YOLO_IMPORT_ERROR})" if YOLO_IMPORT_ERROR else "")
            )
            raise HTTPException(status_code=503, detail=self._error)

        ckpt_path = _resolve_detector_checkpoint()
        if not ckpt_path.exists():
            self._error = f"Không tìm thấy model detect tại: {ckpt_path}"
            raise HTTPException(status_code=503, detail=self._error)

        model = YOLO(str(ckpt_path))
        names = getattr(model, "names", None)
        if isinstance(names, dict) and names:
            self._class_names = [str(names[k]).replace("_", " ") for k in sorted(names.keys())]
        elif isinstance(names, list) and names:
            self._class_names = [str(x).replace("_", " ") for x in names]
        else:
            self._class_names = list(CLASS_NAMES.values())
        self._model = model
        self._loaded_ckpt = ckpt_path
        self._error = None
        state.log(f"Đã nạp model YOLO detect: {ckpt_path.name}")

    def predict(self, img: Image.Image, conf_threshold: float = 0.35) -> tuple[bytes, list[dict[str, Any]], str]:
        with self._lock:
            self._load_if_needed()
            assert self._model is not None
            result = self._model.predict(img, conf=conf_threshold, verbose=False)[0]

        detections: list[dict[str, Any]] = []
        draw = ImageDraw.Draw(img)
        boxes = getattr(result, "boxes", None)
        if boxes is not None:
            for i in range(len(boxes)):
                score = float(boxes.conf[i].item())
                label_idx = int(boxes.cls[i].item())
                name = (
                    self._class_names[label_idx]
                    if 0 <= label_idx < len(self._class_names)
                    else f"Class {label_idx}"
                )
                x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i].tolist()]
                color = (37, 99, 235) if "Virus" not in name else (220, 38, 38)
                draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                label_text = f"{name} {score:.2f}"
                text_y = max(0.0, y1 - 26)
                text_bbox = draw.textbbox((x1 + 6, text_y + 4), label_text, font=VI_FONT)
                draw.rectangle([x1, text_y, text_bbox[2] + 8, text_bbox[3] + 4], fill=color)
                draw.text((x1 + 6, text_y + 4), label_text, fill=(255, 255, 255), font=VI_FONT)
                detections.append(
                    {
                        "class_id": label_idx,
                        "name": name,
                        "confidence": round(score, 4),
                        "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    }
                )

        detections.sort(key=lambda x: float(x["confidence"]), reverse=True)
        top = detections[0]["name"] if detections else "Không phát hiện"
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue(), detections, top


detector = DetectionEngine()


def _scan_dataset_split(split: str) -> list[FrameItem]:
    images_dir = DATASET_DIR / split / "images"
    labels_dir = DATASET_DIR / split / "labels"
    if not images_dir.exists() or not labels_dir.exists():
        return []

    out: list[FrameItem] = []
    for image_path in images_dir.iterdir():
        if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        label_path = labels_dir / f"{image_path.stem}.txt"
        if label_path.exists():
            out.append(FrameItem(split=split, image_path=image_path, label_path=label_path))
    out.sort(key=lambda x: x.image_path.name)
    return out


def _parse_yolo_label_line(line: str) -> tuple[int, float, float, float, float]:
    parts = line.strip().split()
    if len(parts) < 5:
        raise ValueError("Label không hợp lệ")
    cls_id = int(float(parts[0]))
    x_center = float(parts[1])
    y_center = float(parts[2])
    box_w = float(parts[3])
    box_h = float(parts[4])
    return cls_id, x_center, y_center, box_w, box_h


def _draw_bbox(img: Image.Image, label_path: Path) -> tuple[Image.Image, list[dict[str, Any]]]:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    detections: list[dict[str, Any]] = []

    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        cls_id, xc, yc, bw, bh = _parse_yolo_label_line(raw_line)
        x1 = max(0, (xc - bw / 2) * w)
        y1 = max(0, (yc - bh / 2) * h)
        x2 = min(w, (xc + bw / 2) * w)
        y2 = min(h, (yc + bh / 2) * h)
        color = (37, 99, 235) if cls_id != 2 else (220, 38, 38)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        name = CLASS_NAMES.get(cls_id, f"Class {cls_id}")
        text_y = max(0, y1 - 26)
        # Dùng textbbox + font Unicode để giữ dấu tiếng Việt trên ảnh.
        text_bbox = draw.textbbox((x1 + 6, text_y + 4), name, font=VI_FONT)
        bg_x2 = min(w, text_bbox[2] + 8)
        bg_y2 = min(h, text_bbox[3] + 4)
        draw.rectangle([x1, text_y, bg_x2, bg_y2], fill=color)
        draw.text((x1 + 6, text_y + 4), name, fill=(255, 255, 255), font=VI_FONT)
        detections.append(
            {
                "class_id": cls_id,
                "name": name,
                "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            }
        )

    return img, detections


def _get_frame_item(split: str, index: int) -> FrameItem:
    if split not in state.items_by_split:
        raise HTTPException(status_code=400, detail=f"split không hợp lệ: {split}")
    items = state.items_by_split[split]
    if not items:
        raise HTTPException(status_code=404, detail=f"Không có dữ liệu ở split '{split}'")
    if index < 0 or index >= len(items):
        raise HTTPException(status_code=400, detail=f"index ngoài phạm vi: {index}")
    return items[index]


def _capture_dataset_frame(split: str) -> tuple[bytes, str]:
    if split not in state.items_by_split:
        raise HTTPException(status_code=400, detail=f"split không hợp lệ: {split}")
    items = state.items_by_split[split]
    if not items:
        raise HTTPException(status_code=404, detail=f"Không có ảnh ở split '{split}'")

    with state.lock:
        idx = state.frame_idx_by_split[split]
        state.frame_idx_by_split[split] = (idx + 1) % len(items)
    item = items[idx]
    img = Image.open(item.image_path).convert("RGB")
    img, detections = _draw_bbox(img, item.label_path)
    top = detections[0]["name"] if detections else "Không phát hiện"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), f"dataset_{split}_{idx}_{top}"


def _capture_rtsp_frame() -> tuple[bytes, str]:
    if not rtsp_stream.enabled:
        raise HTTPException(
            status_code=503,
            detail="RTSP chưa cấu hình (CAM_RTSP_URL) hoặc thiếu OpenCV.",
        )
    with rtsp_stream.lock:
        data = bytes(rtsp_stream.last_jpeg)
    if not data:
        raise HTTPException(status_code=503, detail="RTSP chưa có frame để chụp.")
    return data, "rtsp"


def _save_capture(data: bytes, prefix: str, subdir: str | None = None) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_prefix = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in prefix)[:60]
    filename = f"{safe_prefix}_{ts}.jpg"
    folder = state.capture_dir
    if subdir:
        folder = folder / subdir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_bytes(data)
    # Trả về đường dẫn tương đối so với captures để UI/API dễ phân biệt nhóm ảnh.
    return str(path.relative_to(state.capture_dir))


def _run_burst_capture(
    count: int,
    interval_sec: float,
    source: str,
    split: str,
    save_subdir: str | None = None,
) -> list[str]:
    out: list[str] = []
    source_key = source.lower().strip()
    for i in range(count):
        if source_key == "rtsp":
            data, prefix = _capture_rtsp_frame()
        elif source_key == "dataset":
            data, prefix = _capture_dataset_frame(split)
        else:
            raise HTTPException(status_code=400, detail="source phải là 'rtsp' hoặc 'dataset'.")
        out.append(_save_capture(data, prefix, subdir=save_subdir))
        if i < count - 1:
            time.sleep(interval_sec)
    return out


def _schedule_runner(job: dict[str, Any]) -> None:
    run_at: datetime = job["run_at_dt"]
    sleep_sec = max(0.0, (run_at - datetime.now()).total_seconds())
    if sleep_sec > 0:
        time.sleep(sleep_sec)
    with state.schedule_lock:
        current = state.schedule_job
        if (
            not current
            or current.get("id") != job["id"]
            or current.get("status") != "scheduled"
        ):
            return

    try:
        files = _run_burst_capture(
            count=int(job["count"]),
            interval_sec=float(job["interval_sec"]),
            source=str(job["source"]),
            split=str(job["split"]),
            save_subdir=str(job.get("save_subdir") or "schedule"),
        )
        with state.schedule_lock:
            if state.schedule_job and state.schedule_job.get("id") == job["id"]:
                state.schedule_job["status"] = "done"
                state.schedule_job["completed_at"] = datetime.now().isoformat(timespec="seconds")
                state.schedule_job["captured_files"] = files
                state.schedule_job["saved_dir"] = str(state.capture_dir / str(job.get("save_subdir") or "schedule"))
        state.log(
            f"Hẹn giờ chụp hoàn tất: {len(files)} ảnh ({job['source']}, mỗi {job['interval_sec']}s)."
        )
    except Exception as exc:
        with state.schedule_lock:
            if state.schedule_job and state.schedule_job.get("id") == job["id"]:
                state.schedule_job["status"] = "error"
                state.schedule_job["error"] = str(exc)
        state.log(f"Hẹn giờ chụp lỗi: {exc}")


@app.on_event("startup")
def startup() -> None:
    for split in ("train", "valid", "test"):
        state.items_by_split[split] = _scan_dataset_split(split)
    total = sum(len(v) for v in state.items_by_split.values())
    state.log(f"Khởi động hệ thống. Tải {total} ảnh có nhãn từ dataset.")
    rtsp_stream.start()
    if not rtsp_stream.url:
        state.log(
            "RTSP: chưa cấu hình — tạo TomatoLeaf_v2/.env từ .env.example hoặc set CAM_RTSP_URL."
        )
    elif not CV2_AVAILABLE:
        state.log("RTSP: chưa cài opencv-python-headless — không thể đọc luồng.")


@app.on_event("shutdown")
def shutdown() -> None:
    rtsp_stream.stop()


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(str(WEB_UI_DIR / "index.html"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dataset/stats")
def dataset_stats() -> dict[str, Any]:
    return {
        "splits": {k: len(v) for k, v in state.items_by_split.items()},
        "classes": CLASS_NAMES,
    }


@app.get("/api/camera/next")
def camera_next(split: str = "train") -> dict[str, Any]:
    if split not in state.items_by_split:
        raise HTTPException(status_code=400, detail=f"split không hợp lệ: {split}")
    items = state.items_by_split[split]
    if not items:
        raise HTTPException(status_code=404, detail=f"Không có ảnh ở split '{split}'")

    with state.lock:
        idx = state.frame_idx_by_split[split]
        state.frame_idx_by_split[split] = (idx + 1) % len(items)

    item = items[idx]
    img = Image.open(item.image_path).convert("RGB")
    _, detections = _draw_bbox(img, item.label_path)
    top = detections[0]["name"] if detections else "Không phát hiện"
    state.log(f"Phân tích ảnh #{idx} ({split}) => {top}")
    return {
        "split": split,
        "index": idx,
        "filename": item.image_path.name,
        "top_disease": top,
        "image_url": f"/api/camera/frame.jpg?split={split}&index={idx}&t={int(datetime.now().timestamp())}",
        "num_detections": len(detections),
        "detections": detections,
    }


@app.get("/api/camera/frame.jpg")
def camera_frame(split: str = "train", index: int = 0) -> StreamingResponse:
    item = _get_frame_item(split, index)
    img = Image.open(item.image_path).convert("RGB")
    img, _ = _draw_bbox(img, item.label_path)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/jpeg")


@app.get("/api/camera/stream/info")
def camera_stream_info() -> dict[str, Any]:
    return {
        "rtsp_configured": bool(rtsp_stream.url),
        "opencv_available": CV2_AVAILABLE,
        "stream_ready": rtsp_stream.enabled,
        "has_live_frame": rtsp_stream.has_live_frame,
        "stream_url": "/api/camera/rtsp/stream.mjpg" if rtsp_stream.enabled else None,
        "snapshot_url": "/api/camera/rtsp/snapshot.jpg" if rtsp_stream.enabled else None,
        "masked_rtsp": RtspStreamManager._mask_url(rtsp_stream.url) if rtsp_stream.url else "",
        "error": rtsp_stream.error,
    }


@app.post("/api/camera/detect")
async def camera_detect(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File detect phải là ảnh.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Ảnh rỗng.")
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Không đọc được ảnh: {exc}") from exc

    conf = float(os.getenv("DETECT_CONF", "0.35"))
    annotated, detections, top = detector.predict(img, conf_threshold=conf)
    data_url = "data:image/jpeg;base64," + base64.b64encode(annotated).decode("ascii")
    state.log(f"Detect ảnh chụp => {top} ({len(detections)} bbox)")
    return {
        "top_disease": top,
        "num_detections": len(detections),
        "detections": detections,
        "image_data_url": data_url,
    }


@app.get("/api/camera/rtsp/stream.mjpg")
def rtsp_mjpeg_stream() -> StreamingResponse:
    if not rtsp_stream.enabled:
        raise HTTPException(
            status_code=503,
            detail="RTSP chưa cấu hình (CAM_RTSP_URL) hoặc thiếu OpenCV.",
        )

    def gen() -> Any:
        boundary = b"frame"
        while True:
            with rtsp_stream.lock:
                chunk = rtsp_stream.last_jpeg
            yield (
                b"--"
                + boundary
                + b"\r\nContent-Type: image/jpeg\r\n\r\n"
                + chunk
                + b"\r\n"
            )
            time.sleep(1 / 12)

    return StreamingResponse(
        gen(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/camera/rtsp/snapshot.jpg")
def rtsp_snapshot() -> Response:
    if not rtsp_stream.enabled:
        raise HTTPException(
            status_code=503,
            detail="RTSP chưa cấu hình (CAM_RTSP_URL) hoặc thiếu OpenCV.",
        )
    with rtsp_stream.lock:
        data = bytes(rtsp_stream.last_jpeg)
    return Response(content=data, media_type="image/jpeg")


@app.post("/api/camera/capture/burst")
def camera_capture_burst(payload: CaptureBurstPayload) -> dict[str, Any]:
    source = payload.source.lower().strip()
    split = payload.split.lower().strip()
    files = _run_burst_capture(
        count=payload.count,
        interval_sec=payload.interval_sec,
        source=source,
        split=split,
        save_subdir="burst",
    )
    state.log(
        f"Chụp liên tiếp: {len(files)} ảnh ({source}, mỗi {payload.interval_sec}s)."
    )
    return {
        "ok": True,
        "count": len(files),
        "interval_sec": payload.interval_sec,
        "source": source,
        "split": split,
        "saved_dir": str(state.capture_dir / "burst"),
        "files": files,
    }


@app.post("/api/camera/capture/schedule")
def camera_capture_schedule(payload: CaptureSchedulePayload) -> dict[str, Any]:
    source = payload.source.lower().strip()
    split = payload.split.lower().strip()
    try:
        run_at = datetime.fromisoformat(payload.run_at)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="run_at không hợp lệ (ISO datetime).") from exc
    if run_at <= datetime.now():
        raise HTTPException(status_code=400, detail="Thời điểm hẹn giờ phải ở tương lai.")
    if source not in {"rtsp", "dataset"}:
        raise HTTPException(status_code=400, detail="source phải là 'rtsp' hoặc 'dataset'.")
    if source == "dataset" and split not in state.items_by_split:
        raise HTTPException(status_code=400, detail=f"split không hợp lệ: {split}")

    schedule_count = 1  # Hẹn giờ luôn chụp đúng 1 ảnh để tránh nhầm với burst.

    with state.schedule_lock:
        old = state.schedule_job
        if old and old.get("status") == "scheduled":
            raise HTTPException(status_code=409, detail="Đang có một lịch chụp đang chờ.")
        job_id = f"job_{int(time.time())}"
        job: dict[str, Any] = {
            "id": job_id,
            "status": "scheduled",
            "run_at": run_at.isoformat(timespec="seconds"),
            "run_at_dt": run_at,
            "count": schedule_count,
            "interval_sec": payload.interval_sec,
            "source": source,
            "split": split,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "captured_files": [],
            "error": None,
            "save_subdir": f"schedule/{job_id}",
            "saved_dir": str(state.capture_dir / f"schedule/{job_id}"),
        }
        state.schedule_job = job
        t = threading.Thread(target=_schedule_runner, args=(job,), daemon=True, name=f"capture-{job_id}")
        t.start()

    state.log(
        f"Đã hẹn chụp lúc {job['run_at']}: {schedule_count} ảnh ({source})."
    )
    return {
        "ok": True,
        "job_id": job_id,
        "status": "scheduled",
        "run_at": job["run_at"],
    }


@app.get("/api/camera/capture/schedule")
def camera_capture_schedule_status() -> dict[str, Any]:
    with state.schedule_lock:
        job = state.schedule_job
        if not job:
            return {"has_job": False}
        return {
            "has_job": True,
            "job_id": job.get("id"),
            "status": job.get("status"),
            "run_at": job.get("run_at"),
            "count": job.get("count"),
            "interval_sec": job.get("interval_sec"),
            "source": job.get("source"),
            "split": job.get("split"),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "error": job.get("error"),
            "captured_files": job.get("captured_files", []),
            "saved_dir": job.get("saved_dir", str(state.capture_dir / "schedule")),
        }


@app.post("/api/camera/capture/schedule/cancel")
def camera_capture_schedule_cancel() -> dict[str, Any]:
    with state.schedule_lock:
        job = state.schedule_job
        if not job or job.get("status") != "scheduled":
            return {"ok": True, "cancelled": False}
        job["status"] = "cancelled"
    state.log("Đã huỷ lịch chụp.")
    return {"ok": True, "cancelled": True}


@app.get("/api/sensors")
def sensor_data() -> dict[str, Any]:
    # Mock dữ liệu dao động nhẹ để UI động.
    with state.lock:
        state.sensor["temperature"] = round(29 + random.random() * 4.5, 1)
        state.sensor["humidity"] = round(50 + random.random() * 10.0, 1)
        state.sensor["light"] = round(150 + random.random() * 90.0, 1)
        state.sensor["soil"] = round(18 + random.random() * 16.0, 1)
        out = dict(state.sensor)
    return {
        **out,
        "updated_at": datetime.now().strftime("%H:%M:%S"),
    }


@app.get("/api/system/state")
def system_state() -> dict[str, Any]:
    return {"manual": state.manual, "devices": state.devices}


@app.post("/api/control/mode")
def control_mode(payload: ModePayload) -> dict[str, Any]:
    state.manual = payload.manual
    state.log("Chuyển chế độ THỦ CÔNG." if payload.manual else "Chuyển chế độ TỰ ĐỘNG.")
    return {"ok": True, "manual": state.manual}


@app.post("/api/control/device")
def control_device(payload: DevicePayload) -> dict[str, Any]:
    if payload.device not in state.devices:
        raise HTTPException(status_code=400, detail=f"Thiết bị không hỗ trợ: {payload.device}")
    if not state.manual:
        raise HTTPException(status_code=409, detail="Đang ở chế độ tự động, không thể bật/tắt thủ công.")
    state.devices[payload.device] = payload.state
    status = "BẬT" if payload.state else "TẮT"
    state.log(f"Thiết bị {payload.device}: {status}.")
    return {"ok": True, "device": payload.device, "state": payload.state}


def _get_ptz_client() -> Any:
    if state.ptz_client is not None:
        return state.ptz_client
    try:
        from onvif import ONVIFCamera
    except Exception:
        return None

    cam_ip = os.getenv("CAM_IP", "")
    cam_user = os.getenv("CAM_USER", "admin")
    cam_pass = os.getenv("CAM_PASS", "")
    onvif_port = int(os.getenv("ONVIF_PORT", "80"))
    if not cam_ip or not cam_pass:
        return None

    try:
        cam = ONVIFCamera(cam_ip, onvif_port, cam_user, cam_pass)
        media = cam.create_media_service()
        ptz = cam.create_ptz_service()
        profiles = media.GetProfiles()
        profile = profiles[0]
        state.ptz_client = {"ptz": ptz, "profile_token": profile.token}
        state.log(f"Kết nối PTZ ONVIF thành công tại {cam_ip}:{onvif_port}.")
        return state.ptz_client
    except Exception as exc:
        state.log(f"Không kết nối được PTZ ONVIF: {exc}. Chuyển sang mock.")
        return None


@app.post("/api/camera/ptz")
def camera_ptz(payload: PtzPayload) -> JSONResponse:
    action = payload.action.lower().strip()
    allowed = {"up", "down", "left", "right", "zoom_in", "zoom_out", "stop"}
    if action not in allowed:
        raise HTTPException(status_code=400, detail=f"Lệnh PTZ không hợp lệ: {action}")

    client = _get_ptz_client()
    if client is None:
        state.log(f"PTZ (mock): {action}")
        return JSONResponse({"ok": True, "action": action, "mode": "mock"})

    ptz = client["ptz"]
    profile_token = client["profile_token"]
    if action == "stop":
        ptz.Stop({"ProfileToken": profile_token})
        state.log("PTZ: STOP")
        return JSONResponse({"ok": True, "action": "stop", "mode": "onvif"})

    vx = vy = vz = 0.0
    speed = 0.45
    if action == "up":
        vy = speed
    elif action == "down":
        vy = -speed
    elif action == "left":
        vx = -speed
    elif action == "right":
        vx = speed
    elif action == "zoom_in":
        vz = speed
    elif action == "zoom_out":
        vz = -speed

    req = ptz.create_type("ContinuousMove")
    req.ProfileToken = profile_token
    req.Velocity = {}
    if vx != 0.0 or vy != 0.0:
        req.Velocity["PanTilt"] = {"x": vx, "y": vy}
    if vz != 0.0:
        req.Velocity["Zoom"] = {"x": vz}
    ptz.ContinuousMove(req)
    state.log(f"PTZ ONVIF: {action}")
    return JSONResponse({"ok": True, "action": action, "mode": "onvif"})


@app.get("/api/logs")
def get_logs(limit: int = 30) -> list[dict[str, str]]:
    return list(state.logs)[: max(1, min(limit, 200))]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_server:app", host="0.0.0.0", port=5500, reload=True)
