#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lập lịch mỗi giờ quay camera PTZ theo kiểu ContinuousMove (nhích theo thời gian).

Lý do: nhiều EZVIZ/Hikvision chỉ công bố ONVIF dạng ContinuousPanTiltVelocitySpace (-1..1),
không cung bố Absolute pan/tilt angle => không dùng được AbsoluteMove.

Mỗi giờ script sẽ:
- nhích pan/tilt trong vài giây (duration)
- gọi Stop để dừng hẳn
"""

import os
import time
from urllib.parse import quote
from datetime import datetime, timedelta
from typing import Optional, Any


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    return val if val not in (None, "") else default


def _check_onvif_port(port: int) -> None:
    if port in (554, 8554):
        raise RuntimeError(
            f"ONVIF_PORT={port} là cổng RTSP. Đặt ONVIF_PORT=80 (HTTP ONVIF) hoặc cổng HTTP đúng của camera."
        )


def main() -> None:
    # ===================== CONFIG =====================
    INTERVAL_MINUTES = 5  # chạy mỗi 5 phút

    # ContinuousMove dùng "velocity" (chuẩn hoá -1..1 tuỳ camera).
    PAN_VEL = 0.5
    TILT_VEL = 0.0
    ZOOM_VEL = 0.0

    # Nhích bao lâu mỗi lần (giây)
    NUDGE_DURATION = 2.0

    # Mỗi giờ đảo chiều pan để quét qua lại.
    TOGGLE_DIRECTION = True
    # ==================================================

    # ---- RTSP display (imshow) ----
    # Mục tiêu: vừa quay PTZ vừa hiển thị video.
    DISPLAY_IMSHOW = True
    WINDOW_NAME = "Camera RTSP (PTZ schedule)"

    # Nếu bạn có sẵn RTSP_URL đầy đủ (đã encode password nếu cần), set RTSP_URL và script sẽ dùng nó.
    RTSP_URL = os.getenv("RTSP_URL", "").strip()

    # Nếu không có RTSP_URL, script sẽ tự dựng RTSP từ các biến sau:
    RTSP_USER = os.getenv("RTSP_USER", os.getenv("CAM_USER", "admin"))
    RTSP_PASS = os.getenv("RTSP_PASS", None)  # nên set riêng nếu RTSP pass != ONVIF pass
    RTSP_HOST = os.getenv("RTSP_HOST", "192.168.1.57")
    RTSP_PORT = os.getenv("RTSP_PORT", "554")
    RTSP_PATH = os.getenv("RTSP_PATH", "/cam/realmonitor?channel=1&subtype=0")
    # --------------------------------

    cam_ip = _get_env("CAM_IP", "192.168.1.57")
    onvif_port = int(_get_env("ONVIF_PORT", "80"))
    username = _get_env("CAM_USER", "admin")
    password = _get_env("CAM_PASS", None)
    if not password:
        raise RuntimeError("Thiếu CAM_PASS. Hãy set biến môi trường CAM_PASS trước khi chạy.")

    _check_onvif_port(onvif_port)

    from onvif import ONVIFCamera
    from onvif_ptz_utils import select_profile_with_ptz

    cap = None
    if DISPLAY_IMSHOW:
        try:
            import cv2  # import muộn để không bắt buộc nếu không hiển thị
        except Exception as e:
            raise RuntimeError(
                "DISPLAY_IMSHOW đang bật nhưng không import được OpenCV (cv2). "
                "Hãy cài `opencv-python` hoặc tắt DISPLAY_IMSHOW."
            ) from e

        if not RTSP_URL:
            if not RTSP_PASS:
                # Nếu người dùng không cung cấp RTSP_PASS thì fallback sang CAM_PASS (có thể sai nếu 2 pass khác nhau)
                RTSP_PASS = password
            rtsp_pass_enc = quote(RTSP_PASS, safe="")
            RTSP_URL = (
                f"rtsp://{RTSP_USER}:{rtsp_pass_enc}@{RTSP_HOST}:{RTSP_PORT}{RTSP_PATH}"
            )

        cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            raise RuntimeError(f"Không mở được RTSP để hiển thị: {RTSP_URL}")

    print(f"Kết nối ONVIF: {cam_ip}:{onvif_port} ...")
    cam = ONVIFCamera(cam_ip, onvif_port, username, password)
    media = cam.create_media_service()
    ptz = cam.create_ptz_service()

    profiles = media.GetProfiles()
    profile = select_profile_with_ptz(profiles)
    profile_token = profile.token

    def stop() -> None:
        try:
            ptz.Stop({"ProfileToken": profile_token})
        except Exception:
            pass

    def nudge(pan_vel: float, tilt_vel: float, zoom_vel: float, duration: float) -> None:
        req = ptz.create_type("ContinuousMove")
        req.ProfileToken = profile_token
        req.Velocity = {}
        if pan_vel != 0.0 or tilt_vel != 0.0:
            req.Velocity["PanTilt"] = {"x": float(pan_vel), "y": float(tilt_vel)}
        if zoom_vel != 0.0:
            req.Velocity["Zoom"] = {"x": float(zoom_vel)}

        ptz.ContinuousMove(req)
        time.sleep(duration)
        stop()

    stop()

    direction = 1.0
    print("Bắt đầu lịch mỗi 5 phút (ContinuousMove). Nhấn Ctrl+C để dừng.")
    while True:
        now = datetime.now()
        # Tính mốc chạy tiếp theo (bội số của INTERVAL_MINUTES)
        bucket = (now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES
        next_bucket = bucket + INTERVAL_MINUTES
        next_time = now.replace(second=0, microsecond=0)
        if next_bucket >= 60:
            next_time = next_time + timedelta(hours=1)
            next_time = next_time.replace(minute=next_bucket - 60)
        else:
            next_time = next_time.replace(minute=next_bucket)

        # Loop đọc frame liên tục; khi tới thời điểm thì nhích PTZ một lần.
        while True:
            # Nếu tới lịch -> nhích
            if datetime.now() >= next_time:
                pan_vel = direction * PAN_VEL if TOGGLE_DIRECTION else PAN_VEL
                print(
                    f"[{datetime.now().isoformat(sep=' ', timespec='seconds')}] "
                    f"ContinuousMove pan_vel={pan_vel}, tilt_vel={TILT_VEL}, duration={NUDGE_DURATION}s"
                )
                nudge(
                    pan_vel=pan_vel,
                    tilt_vel=TILT_VEL,
                    zoom_vel=ZOOM_VEL,
                    duration=NUDGE_DURATION,
                )
                if TOGGLE_DIRECTION:
                    direction *= -1.0
                break

            # Hiển thị RTSP (nếu bật)
            if cap is not None:
                ret, frame = cap.read()
                if ret and frame is not None:
                    cv2.imshow(WINDOW_NAME, frame)
                    # Q để thoát hiển thị
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        raise KeyboardInterrupt()
                else:
                    # Nếu không đọc được frame thì chờ nhẹ để tránh busy loop
                    time.sleep(0.05)
            else:
                # Không hiển thị -> chờ kiểm tra lịch
                time.sleep(0.1)

            # Giảm tần suất kiểm tra thời gian
            time.sleep(0.01)

    # (Không tới được vì while True)


if __name__ == "__main__":
    main()

