# TomatoLeaf v2

Dashboard điều khiển nhà kính có backend thật (FastAPI) + web UI tiếng Việt.

## Thành phần

- `web_server.py`: API + phục vụ UI + lấy ảnh dataset và vẽ bounding box.
- `web_ui/`: giao diện dashboard điều khiển.
- `camera_control/`: các script ONVIF/PTZ gốc.
- `models/best.pt`: trọng số YOLO đã huấn luyện (phục vụ suy luận / mở rộng; UI mặc định vẫn có thể dựa trên nhãn YOLO trong dataset).

## Chạy hệ thống web điều khiển

Từ thư mục `TomatoLeaf_v2`:

```bash
python web_server.py
```

Hoặc:

```bash
uvicorn web_server:app --host 0.0.0.0 --port 5500 --reload
```

Mở:

- [http://localhost:5500](http://localhost:5500)

## Tính năng hiện có

- Camera giả lập từ `dataset_detection` (`train/valid/test`) và hiển thị ảnh có **bounding box**.
- Dữ liệu cảm biến + trạng thái thiết bị qua API.
- Nhật ký hệ thống lấy từ backend.
- Điều khiển thiết bị (thủ công/tự động).
- Điều khiển PTZ qua API:
  - Nếu có cấu hình ONVIF (`CAM_IP`, `CAM_USER`, `CAM_PASS`, `ONVIF_PORT`) thì gửi lệnh thật.
  - Nếu chưa cấu hình thì chạy mock để test UI.

## Biến môi trường PTZ (tuỳ chọn)

```bash
CAM_IP=192.168.1.57
CAM_USER=admin
CAM_PASS=your_password
ONVIF_PORT=80
```
