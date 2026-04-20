# -*- coding: utf-8 -*-
"""
Điều khiển PTZ qua ONVIF bằng phím:
  W: lên, S: xuống, A: trái, D: phải
  Q: zoom in, E: zoom out
  X: dừng, Esc: thoát
"""

import time
import sys
import os

# ---- Cấu hình camera của bạn ----
CAM_IP = os.getenv("CAM_IP", "192.168.1.57")
ONVIF_PORT = int(os.getenv("ONVIF_PORT", "80"))  # EZVIZ/Hikvision thường là 80 (không phải 554)
USERNAME = os.getenv("CAM_USER", "admin")
PASSWORD = os.getenv("CAM_PASS", "")
NUDGE_TIME = 0.3          # thời gian "nhích" mỗi lần nhấn phím (giây)
SPEED_PAN = 0.5           # [-1.0, 1.0]
SPEED_TILT = 0.5          # [-1.0, 1.0]
SPEED_ZOOM = 0.5          # [-1.0, 1.0]
# ----------------------------------

# getch cross-platform
def getch():
    try:
        # Windows
        import msvcrt
        ch = msvcrt.getch()
        # msvcrt trả về b'\xe0' hoặc b'\x00' cho phím đặc biệt -> đọc thêm
        if ch in (b'\x00', b'\xe0'):
            ch = msvcrt.getch()
        return ch.decode(errors="ignore").lower()
    except ImportError:
        # Unix
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def main():
    from onvif import ONVIFCamera

    if not PASSWORD:
        raise RuntimeError(
            "Thiếu mật khẩu ONVIF: hãy set biến môi trường CAM_PASS (ví dụ: $env:CAM_PASS=\"UIZCHI\")."
        )

    print(f"Kết nối ONVIF tới {CAM_IP}:{ONVIF_PORT} ...")
    cam = ONVIFCamera(CAM_IP, ONVIF_PORT, USERNAME, PASSWORD)
    media = cam.create_media_service()
    ptz = cam.create_ptz_service()

    profiles = media.GetProfiles()
    if not profiles:
        print("Không lấy được profile media. Hãy kiểm tra ONVIF đã bật và user có quyền.")
        return
    profile = profiles[0]  # thường lấy profile đầu tiên
    profile_token = profile.token

    # Hàm dừng PTZ
    def stop():
        try:
            ptz.Stop({"ProfileToken": profile_token})
        except Exception:
            pass  # nhiều model trả lỗi nếu đang không di chuyển

    # Hàm di chuyển "nhích" theo vận tốc trong thời gian ngắn rồi dừng
    def nudge(pan=0.0, tilt=0.0, zoom=0.0, duration=NUDGE_TIME):
        req = ptz.create_type("ContinuousMove")
        req.ProfileToken = profile_token
        req.Velocity = {}
        if pan != 0.0 or tilt != 0.0:
            req.Velocity["PanTilt"] = {"x": float(pan), "y": float(tilt)}
        if zoom != 0.0:
            req.Velocity["Zoom"] = {"x": float(zoom)}
        # Bắt đầu
        ptz.ContinuousMove(req)
        time.sleep(duration)
        # Dừng
        stop()

    print(
        "\nĐiều khiển PTZ:\n"
        "  W: lên, S: xuống, A: trái, D: phải\n"
        "  Q: zoom in, E: zoom out\n"
        "  X: dừng, Esc: thoát\n"
    )

    # đảm bảo dừng trước khi bắt đầu
    stop()

    while True:
        ch = getch()
        if ch == "\x1b":  # Esc
            stop()
            print("Thoát.")
            break
        elif ch == "w":
            nudge(tilt=+SPEED_TILT)
        elif ch == "s":
            nudge(tilt=-SPEED_TILT)
        elif ch == "a":
            nudge(pan=-SPEED_PAN)
        elif ch == "d":
            nudge(pan=+SPEED_PAN)
        elif ch == "q":
            # Một số camera EZVIZ chỉ hỗ trợ Pan/Tilt, không hỗ trợ Zoom qua ONVIF PTZ Node.
            try:
                nudge(zoom=+SPEED_ZOOM)
            except Exception as e:
                print("Zoom (Q) không hỗ trợ trên PTZ Node của camera:", e)
                continue
        elif ch == "e":
            try:
                nudge(zoom=-SPEED_ZOOM)
            except Exception as e:
                print("Zoom (E) không hỗ trợ trên PTZ Node của camera:", e)
                continue
        elif ch == "x":
            stop()
        # bỏ qua các phím khác

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Lỗi:", e)
        print("Gợi ý kiểm tra:")
        print("  • Đã bật ONVIF trong cài đặt camera chưa?")
        print("  • User/pass ONVIF đúng chưa (có thể khác tài khoản RTSP)?")
        print("  • Cổng ONVIF (thường 80) có đúng không, có bị chặn firewall không?")
