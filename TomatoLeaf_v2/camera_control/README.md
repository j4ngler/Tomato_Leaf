## Camera control (chỉ xử lý phần camera)

Folder này dùng để chứa code/logic điều khiển camera và lịch quay theo thời gian (ví dụ PTZ/pan-tilt hoặc camera gắn motor).

### Gợi ý kiến trúc (backend)
- `scheduler/`: lập lịch (theo giờ/phút, theo ngày, theo cron)
- `controller/`: điều khiển phần cứng (PTZ via RS-485/ONVIF, hoặc servo stepper qua GPIO/Arduino)
- `profiles/`: cấu hình "chương trình quay" (mỗi khung giờ thì góc quay/độ phơi sáng nào)
- `runtime/`: service chạy nền, expose API/health

### Bạn cần cung cấp thêm để mình triển khai đúng
- Camera của bạn là loại gì: PTZ hỗ trợ ONVIF hay điều khiển motor tự lắp?
- Điều khiển góc theo kiểu nào: "gán góc pan/tilt" hay "quay trái/phải trong X giây"?
- Lịch quay: mỗi ngày mấy lần? khung giờ cụ thể? thứ mấy?

### Cài thư viện ONVIF
- Cài: `uv pip install onvif-zeep` (hoặc `pip install onvif-zeep`)
- **Không** cài gói `onvif` trên PyPI — gói đó phụ thuộc `suds-passworddigest` và thường **build lỗi** trên Python 3.
- Nếu vẫn lỗi trên Python quá mới (ví dụ 3.14), nên tạo venv bằng **Python 3.11 hoặc 3.12**.

### Lịch quay mỗi giờ (theo phần mềm)
Thư mục này có các script mẫu dùng ONVIF để:
- Lấy dải pan/tilt tối thiểu-tối đa từ camera (`camera_control/ptz_limits.py`)
- Mỗi giờ tự quay sang góc pan tiếp theo trong dải (`camera_control/schedule_hourly_ptz.py`)
 - Nếu camera chỉ công bố **Continuous/Velocity** (-1..1) mà không có Absolute angle: dùng (`camera_control/schedule_hourly_continuous_ptz.py`)

Chạy mẫu:
1. Lấy dải pan/tilt (cần bật ONVIF và user có quyền):
   - Set biến môi trường `CAM_PASS`, và (tuỳ chọn) `CAM_IP`, `CAM_USER`, `ONVIF_PORT`
   - **Quan trọng:** `ONVIF_PORT` là cổng **HTTP** ONVIF (thường **80**). **Không** dùng **554** — đó là cổng **RTSP** (xem hình), gửi ONVIF vào 554 sẽ lỗi `RemoteDisconnected`.
   - Chạy: `python camera_control/ptz_limits.py`
2. Lập lịch mỗi giờ:
   - Chạy: `python camera_control/schedule_hourly_ptz.py`
   - Chỉnh `PAN_STEP`, `RUN_MINUTE`, `PAN_SPEED`/`TILT_SPEED` trong file cho phù hợp

Nếu `ptz_limits.py` chỉ ra `ContinuousPanTiltVelocitySpace` (-1..1) (và không có Absolute pan/tilt):
- Chạy thay bằng: `python camera_control/schedule_hourly_continuous_ptz.py`
- Nhích mỗi lần bằng các biến `PAN_VEL` và `NUDGE_DURATION` (cần tinh chỉnh theo thực tế bằng mắt).

Lưu ý: dải trả về từ ONVIF có thể là "độ thật" hoặc "giá trị chuẩn hoá" tuỳ hãng/model. Hãy gửi output của `ptz_limits.py` để mình giúp bạn quy đổi và chọn bước góc.

Nếu báo không có `PTZSpaces`: nhiều **EZVIZ/Hikvision** chỉ trả **`PanTiltLimits`** — script đã đọc được. Nếu vẫn lỗi, chạy `$env:PTZ_DEBUG="1"` rồi `python camera_control/ptz_limits.py` để in cấu trúc `GetConfiguration`.

**EZVIZ:** Camera có thể chỉ công bố **`ContinuousPanTiltVelocitySpace`** với dải **-1..1** — đó là **chuẩn hoá vận tốc** (ContinuousMove), **không** phải góc quay tối đa bằng độ. `schedule_hourly_ptz.py` (AbsoluteMove) cần không gian **Absolute** hoặc **PanTiltLimits**; nếu không có, hãy lập lịch bằng **ContinuousMove** (nhích pan/tilt theo vài giây mỗi giờ), ví dụ chỉnh từ `ptz_wasd.py`.

