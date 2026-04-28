# Hướng dẫn chạy nhanh TomatoLeaf_v2

## 1) Chuẩn bị môi trường

Từ thư mục gốc project:

```bash
python -m venv venv
```

Windows PowerShell:

```bash
.\venv\Scripts\Activate.ps1
```

Cài thư viện:

```bash
pip install -r requirements.txt
```

## 2) Cấu hình camera/model (tuỳ chọn)

- Copy `TomatoLeaf_v2/.env.example` thành `TomatoLeaf_v2/.env` rồi điền RTSP nếu cần.
- Nếu dùng detect YOLO, đặt model tại:
  - `TomatoLeaf_v2/models/best.pt` (ưu tiên), hoặc
  - set biến `YOLO_MODEL_PATH` trỏ tới file `best.pt`.

## 3) Chạy web

```bash
cd TomatoLeaf_v2
python web_server.py
```

Mở trình duyệt:

- [http://localhost:5500](http://localhost:5500)

## 4) Kiểm tra nhanh

- Mở Dashboard hoặc Camera Live.
- Nếu không có RTSP, hệ thống sẽ fallback webcam.
- Bấm **Chụp ảnh** để chụp và detect bệnh ngay.
