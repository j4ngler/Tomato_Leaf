# Hướng dẫn sử dụng hệ thống phát hiện bệnh lá cà chua

Hệ thống gồm: chuẩn bị dataset (3 bệnh), huấn luyện mô hình YOLO, server API và giao diện web để chụp/upload ảnh lá và xem kết quả phát hiện bệnh.

---

## 1. Yêu cầu

- **Python 3.8+**
- Thư viện: `ultralytics`, `torch`, `torchvision`, `fastapi`, `uvicorn`, `Pillow`

Cài đặt:

```powershell
cd D:\BkStar\TomatoLeaf
pip install -r requirements.txt
```

(Nếu bạn train YOLO riêng, cần cài thêm môi trường theo [Ultralytics](https://docs.ultralytics.com/).)

---

## 2. Cấu trúc thư mục chính

```
TomatoLeaf/
├── PlantVillage/          # Dataset gốc (tùy chọn, có thể đặt chỗ khác)
├── dataset/               # 3 lớp: Early_blight, Bacterial_spot, Yellow_Leaf_Curl_Virus
├── dataset_detection/     # Dataset detection (train/valid/test + images + labels)
├── dataset_detection_hub/  # Dataset đúng format Ultralytics Hub (images/train|val|test, labels/..., data.yaml)
├── split_plantvillage.py   # Bước 1: Tách 3 lớp từ PlantVillage → dataset/
├── prepare_ultralytics_dataset.py  # Bước 2: Làm giàu + tạo dataset detection/hub
├── dataloader.py           # Hỗ trợ PyTorch (classification, split, sampler)
├── tomato_leaf.yaml        # Cấu hình dataset (local)
├── server.py               # API + giao diện web
├── static/                 # Giao diện web (index.html, styles.css, app.js)
├── requirements.txt
└── best.pt                 # Model YOLO đã train (bạn cần có file này)
```

---

## 3. Chuẩn bị dữ liệu

### Bước 1: Tách 3 lớp bệnh từ PlantVillage

Nếu bạn có thư mục PlantVillage gốc:

1. Mở `split_plantvillage.py`, kiểm tra:
   - `SRC_ROOT`: đường dẫn tới thư mục PlantVillage
   - `DST_ROOT`: thư mục đích (mặc định `dataset/`)

2. Chạy:

```powershell
python split_plantvillage.py
```

Kết quả: thư mục `dataset/` với 3 thư mục con: `Early_blight/`, `Bacterial_spot/`, `Yellow_Leaf_Curl_Virus/`.

---

### Bước 2: Làm giàu dữ liệu và tạo dataset cho detection / Hub

File `prepare_ultralytics_dataset.py` có nhiều chế độ. Mở file, tìm dòng `MODE = "..."` và đặt một trong các giá trị sau:

| MODE | Mục đích |
|------|----------|
| `enrich_hub` | Làm giàu 6000 ảnh/lớp (18k tổng), ghi trực tiếp vào `dataset_detection_hub` (format Hub). **Nên dùng** nếu bạn muốn 1 bước xong cả làm giàu + chuẩn bị upload Hub. |
| `detection` | Tạo `dataset_detection/` (train/valid/test + images + labels) từ `dataset/`, không làm giàu. |
| `export_hub` | Copy từ `dataset_detection/` sang `dataset_detection_hub/` (đúng cấu trúc Hub). |
| `check` | Kiểm tra dataset detection (ảnh–label khớp, định dạng YOLO). |
| `enrich_6000` | Làm giàu vào thư mục riêng `dataset_enriched_6000/` (cấu trúc classification). |

**Ví dụ: làm giàu và xuất ra Hub (khuyến nghị)**

1. Trong `prepare_ultralytics_dataset.py` đặt: `MODE = "enrich_hub"`.
2. Chạy:

```powershell
python prepare_ultralytics_dataset.py
```

3. Kết quả: `dataset_detection_hub/` có `images/train`, `images/val`, `images/test`, `labels/...`, `data.yaml`. Có thể nén thư mục này thành zip rồi upload lên Ultralytics Hub nếu bạn dùng Hub để train.

**Kiểm tra dataset detection (trước khi train hoặc upload):**

- Đặt `MODE = "check"`, chạy cùng lệnh trên. Script sẽ báo lỗi nếu thiếu ảnh/label hoặc sai định dạng.

---

## 4. Huấn luyện mô hình YOLO

Bạn có thể train trên máy local hoặc trên Ultralytics Hub.

**Local (ví dụ):**

```powershell
yolo detect train data=dataset_detection_hub/data.yaml model=yolov8n.pt epochs=50 imgsz=640
```

Sau khi train xong, file model thường nằm ở dạng: `runs/detect/train/weights/best.pt`. Copy hoặc ghi nhớ đường dẫn này để dùng cho server.

---

## 5. Chạy server và sử dụng giao diện web

### 5.1. Cấu hình đường dẫn model

Mở `server.py`, sửa dòng:

```python
MODEL_PATH = "best.pt"
```

thành đường dẫn thật tới file model, ví dụ:

```python
MODEL_PATH = r"runs/detect/train/weights/best.pt"
```

### 5.2. Khởi động server

```powershell
cd D:\BkStar\TomatoLeaf
python server.py
```

Server chạy tại: **http://localhost:8000**

- **Giao diện web:** mở trình duyệt, truy cập **http://localhost:8000/**
- Trang chủ: nút **Chọn / chụp ảnh** → chọn file ảnh lá từ máy (hoặc trên điện thoại sẽ mở camera) → bấm **Phát hiện bệnh** → kết quả hiển thị bên phải (tên bệnh, độ tin cậy, bbox).

### 5.3. Dùng trên điện thoại (cùng mạng Wi‑Fi)

1. Xác định địa chỉ IP máy tính (ví dụ `192.168.1.10`).
2. Server đã chạy với `host="0.0.0.0"` nên thiết bị khác trong mạng có thể truy cập.
3. Trên điện thoại, mở trình duyệt và vào: **http://192.168.1.10:8000/**
4. Bấm **Chọn / chụp ảnh** → chụp lá → **Phát hiện bệnh** → xem kết quả.
5. (Tùy chọn) Trên điện thoại có thể **Thêm vào màn hình chính** để dùng như app.

---

## 6. API dùng cho ứng dụng khác

Nếu bạn viết app mobile/desktop riêng, có thể gọi API trực tiếp:

- **Kiểm tra server:**  
  `GET http://localhost:8000/health`  
  Trả về: `{"status": "ok"}`

- **Phát hiện bệnh:**  
  `POST http://localhost:8000/predict`  
  - Body: `multipart/form-data`, field tên `file`, giá trị là file ảnh (jpg/png/...).  
  - Trả về JSON ví dụ:

```json
{
  "num_detections": 1,
  "diseases": [
    {
      "class_id": 1,
      "name": "Bacterial_spot",
      "confidence": 0.92,
      "bbox": [100, 50, 400, 380]
    }
  ]
}
```

---

## 7. Tóm tắt quy trình thường dùng

1. **Chuẩn bị dữ liệu:** Chạy `split_plantvillage.py` → có `dataset/`. Sau đó chạy `prepare_ultralytics_dataset.py` với `MODE = "enrich_hub"` → có `dataset_detection_hub/`.
2. **Train model:** Dùng `data.yaml` trong `dataset_detection_hub/` để train YOLO, lấy file `best.pt`.
3. **Chạy hệ thống:** Sửa `MODEL_PATH` trong `server.py` trỏ tới `best.pt`, chạy `python server.py`, mở http://localhost:8000 để dùng web; trên điện thoại dùng http://&lt;IP-máy&gt;:8000.

Nếu gặp lỗi (thiếu ảnh, không tìm thấy model, API lỗi), kiểm tra lại đường dẫn trong từng file và chạy `MODE = "check"` để kiểm tra dataset.
