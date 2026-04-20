# TomatoLeaf v2 — Điều khiển nhà kính & camera

Repo gọn chỉ gồm module **TomatoLeaf v2**: dashboard web (FastAPI), giao diện tiếng Việt, tích hợp luồng camera/RTSP, PTZ (ONVIF hoặc mock), chụp liên tiếp và hẹn giờ chụp.

## Cấu trúc

| Mục | Mô tả |
|-----|--------|
| `TomatoLeaf_v2/web_server.py` | Backend API + phục vụ static UI |
| `TomatoLeaf_v2/web_ui/` | HTML/CSS/JS dashboard |
| `TomatoLeaf_v2/camera_control/` | Script tham khảo: RTSP, PTZ, lịch quay |
| `TomatoLeaf_v2/.env.example` | Mẫu biến môi trường (copy thành `.env`) |
| `requirements.txt` | Phụ thuộc Python để chạy web v2 |

Chi tiết thêm: xem `TomatoLeaf_v2/README.md`.

## Cài đặt

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy

```bash
cd TomatoLeaf_v2
python web_server.py
```

Mở trình duyệt: [http://localhost:5500](http://localhost:5500)

## Ghi chú

- Dataset YOLO (bbox) mặc định đọc từ `../dataset_detection` so với thư mục `TomatoLeaf_v2` (cùng cấp với `TomatoLeaf_v2` trong workspace đầy đủ). Nếu chỉ clone nhánh này, cần đặt dataset đúng đường dẫn tương đối hoặc chỉnh trong `web_server.py`.
- Luồng RTSP cần `opencv-python-headless` và biến môi trường theo `TomatoLeaf_v2/.env.example`.
- Thư mục `TomatoLeaf_v2/captures/` (ảnh chụp burst/lịch) được git bỏ qua; không commit file `.env`.
