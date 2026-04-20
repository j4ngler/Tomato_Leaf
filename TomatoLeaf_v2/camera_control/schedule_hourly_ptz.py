#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lập lịch mỗi giờ để quay camera (PTZ) theo ONVIF.

Cách chạy:
- Set biến môi trường CAM_PASS, CAM_IP (nếu khác), ...
- Chỉnh cấu hình ở phần "CONFIG".

Gợi ý:
- Trước tiên chạy `ptz_limits.py` để biết min/max pan/tilt.
- Sau đó đặt PAN_STEP hoặc đặt dải pan mong muốn.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Any, Optional


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    return val if val not in (None, "") else default


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def _check_onvif_port(port: int) -> None:
    if port in (554, 8554):
        raise RuntimeError(
            f"ONVIF_PORT={port} là cổng RTSP. Đặt ONVIF_PORT=80 (hoặc cổng HTTP ONVIF của camera)."
        )



def _extract_absolute_ranges(ptz: Any, profile: Any) -> tuple[float, float, float, float]:
    from onvif_ptz_utils import (
        extract_pan_tilt_ranges,
        get_ptz_configuration,
        ptz_configuration_token,
    )

    cfg = get_ptz_configuration(ptz, profile)
    tok = ptz_configuration_token(profile)
    pan_min, pan_max, tilt_min, tilt_max, _src = extract_pan_tilt_ranges(
        cfg, ptz=ptz, ptz_cfg_token=tok
    )
    return pan_min, pan_max, tilt_min, tilt_max


def _absolute_move(ptz: Any, profile_token: str, pan: float, tilt: float, pan_speed: float, tilt_speed: float) -> None:
    req = ptz.create_type("AbsoluteMove")
    req.ProfileToken = profile_token

    # ONVIF: Position = { PanTilt: { x: pan, y: tilt }, Zoom: { x: zoom }? }
    req.Position = {"PanTilt": {"x": float(pan), "y": float(tilt)}}

    # Speed: { PanTilt: { x: pan_speed, y: tilt_speed } }
    req.Speed = {"PanTilt": {"x": float(pan_speed), "y": float(tilt_speed)}}

    ptz.AbsoluteMove(req)


def main() -> None:
    # ===================== CONFIG =====================
    # Di chuyển mỗi giờ theo bước pan (đơn vị tuỳ ONVIF: có thể là độ hoặc giá trị chuẩn hoá).
    PAN_STEP = 10.0
    # Tilt giữ cố định.
    TILT_VALUE = None  # nếu None -> lấy trung điểm tilt
    # Tốc độ AbsoluteMove: [-1..1] hoặc theo camera; thử chỉnh nếu chạy quá nhanh/chậm.
    PAN_SPEED = 0.5
    TILT_SPEED = 0.5
    # Muốn dừng khi đạt max/min rồi đảo chiều:
    BOUNCE = True
    # Chọn phút chạy mỗi giờ:
    RUN_MINUTE = 0
    # ==================================================

    cam_ip = _get_env("CAM_IP", "192.168.1.57")
    onvif_port = int(_get_env("ONVIF_PORT", "80"))
    username = _get_env("CAM_USER", "admin")
    password = _get_env("CAM_PASS", None)
    if not password:
        raise RuntimeError("Thiếu CAM_PASS. Hãy set biến môi trường CAM_PASS trước khi chạy.")

    _check_onvif_port(onvif_port)

    from onvif import ONVIFCamera

    print(f"Kết nối ONVIF: {cam_ip}:{onvif_port} ...")
    try:
        cam = ONVIFCamera(cam_ip, onvif_port, username, password)
    except Exception as e:
        err = str(e).lower()
        if "remote" in err or "disconnected" in err or "connection" in err:
            raise RuntimeError(
                "Không nối được ONVIF. Thử ONVIF_PORT=80 (không dùng 554 RTSP). "
                f"Chi tiết: {e}"
            ) from e
        raise
    media = cam.create_media_service()
    ptz = cam.create_ptz_service()

    profiles = media.GetProfiles()
    if not profiles:
        raise RuntimeError("Không lấy được profiles. Kiểm tra ONVIF và user quyền.")

    from onvif_ptz_utils import select_profile_with_ptz

    profile = select_profile_with_ptz(profiles)
    profile_token = profile.token

    pan_min, pan_max, tilt_min, tilt_max = _extract_absolute_ranges(ptz, profile)
    print(f"Absolute pan range: {pan_min} .. {pan_max}")
    print(f"Absolute tilt range: {tilt_min} .. {tilt_max}")

    tilt_value = (tilt_min + tilt_max) / 2 if TILT_VALUE is None else float(TILT_VALUE)

    # Khởi tạo pan ở trung điểm
    pan = (pan_min + pan_max) / 2
    direction = 1.0

    print("Bắt đầu lịch mỗi giờ. Nhấn Ctrl+C để dừng.")
    while True:
        now = datetime.now()
        # Tính thời điểm chạy tiếp theo trong cùng giờ/phút cấu hình.
        next_time = now.replace(minute=RUN_MINUTE, second=0, microsecond=0)
        if next_time <= now:
            next_time = next_time + timedelta(hours=1)

        sleep_s = (next_time - now).total_seconds()
        if sleep_s > 0:
            time.sleep(sleep_s)

        # Tính pan mục tiêu cho lần chạy này
        target_pan = pan + direction * PAN_STEP
        if BOUNCE:
            if target_pan > pan_max:
                target_pan = pan_max
                direction = -1.0
            elif target_pan < pan_min:
                target_pan = pan_min
                direction = 1.0
        else:
            target_pan = max(pan_min, min(pan_max, target_pan))

        target_tilt = max(tilt_min, min(tilt_max, tilt_value))
        print(f"[{datetime.now().isoformat(sep=' ', timespec='seconds')}] Move to pan={target_pan}, tilt={target_tilt}")

        _absolute_move(ptz, profile_token, target_pan, target_tilt, PAN_SPEED, TILT_SPEED)
        pan = target_pan


if __name__ == "__main__":
    main()

