#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
In ra dải PTZ (pan/tilt) tối thiểu/tối đa lấy từ camera qua ONVIF.

Mục tiêu:
- Bạn cần biết "quay được bao nhiêu độ" để lập lịch mỗi giờ quay theo góc cố định.

Lưu ý:
- Dải độ có thể là "độ thật" hoặc "giá trị chuẩn hoá" tuỳ camera ONVIF.
- ONVIF dùng HTTP(S), cổng thường là 80 (hoặc 8000/8080). Cổng 554 là RTSP — không dùng cho ONVIF.
"""

import os
from typing import Any, Optional


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    return val if val not in (None, "") else default


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def _print_range(label: str, space: Any) -> None:
    x_range = _safe_get(space, "XRange")
    y_range = _safe_get(space, "YRange")
    z_range = _safe_get(space, "ZoomRange")

    def fmt_range(r: Any) -> str:
        if r is None:
            return "None"
        rmin = _safe_get(r, "Min")
        rmax = _safe_get(r, "Max")
        unit = _safe_get(r, "Unit", None)
        unit_str = f" {unit}" if unit is not None else ""
        return f"Min={rmin}, Max={rmax}{unit_str}"

    print(f"- {label}")
    print(f"  Pan (XRange): {fmt_range(x_range)}")
    print(f"  Tilt (YRange): {fmt_range(y_range)}")
    print(f"  Zoom (ZoomRange): {fmt_range(z_range)}")


def _check_onvif_port(port: int) -> None:
    """554/8554 là RTSP — gửi SOAP ONVIF vào đó sẽ bị đóng kết nối (RemoteDisconnected)."""
    if port in (554, 8554):
        raise RuntimeError(
            f"ONVIF_PORT={port} là cổng RTSP, không phải ONVIF.\n"
            "Hãy đặt ONVIF_PORT=80 (mặc định EZVIZ/Hikvision) hoặc cổng HTTP trong app/web camera.\n"
            "Ví dụ PowerShell: $env:ONVIF_PORT=\"80\""
        )


def main() -> None:
    # Đặt theo biến môi trường để tránh hardcode mật khẩu
    cam_ip = _get_env("CAM_IP", "192.168.1.57")
    onvif_port = int(_get_env("ONVIF_PORT", "80"))
    username = _get_env("CAM_USER", "admin")
    password = _get_env("CAM_PASS", None)

    if not password:
        raise RuntimeError(
            "Thiếu CAM_PASS. Bạn hãy set biến môi trường CAM_PASS trước khi chạy."
        )

    _check_onvif_port(onvif_port)

    from onvif import ONVIFCamera

    print(f"Kết nối ONVIF: {cam_ip}:{onvif_port} ...")
    try:
        cam = ONVIFCamera(cam_ip, onvif_port, username, password)
    except Exception as e:
        err = str(e).lower()
        if "remote" in err or "disconnected" in err or "connection" in err:
            raise RuntimeError(
                "Không nối được ONVIF (kết nối bị đóng). Kiểm tra:\n"
                "  • ONVIF_PORT phải là cổng HTTP (thường 80), không phải 554 (RTSP).\n"
                "  • Đã bật ONVIF trên camera và user có quyền.\n"
                "  • Thử thêm: $env:ONVIF_PORT=\"8000\" hoặc \"8080\" nếu model dùng cổng khác.\n"
                f"Chi tiết gốc: {e}"
            ) from e
        raise
    media = cam.create_media_service()
    ptz = cam.create_ptz_service()

    profiles = media.GetProfiles()
    if not profiles:
        raise RuntimeError("Không lấy được profiles. Hãy kiểm tra ONVIF đã bật và user có quyền.")

    from onvif_ptz_utils import (
        debug_dump_ptz_configuration,
        describe_velocity_and_relative_spaces,
        extract_pan_tilt_ranges,
        get_ptz_configuration,
        get_ptz_configuration_options,
        ptz_configuration_token,
        select_profile_with_ptz,
    )

    profile = select_profile_with_ptz(profiles)
    profile_token = profile.token
    ptz_cfg_token = ptz_configuration_token(profile)
    cfg = get_ptz_configuration(ptz, profile)

    ptz_spaces = _safe_get(cfg, "PTZSpaces") or _safe_get(cfg, "Spaces")
    if ptz_spaces is not None:
        print("Dải PTZ (theo ONVIF PTZSpaces, nếu camera có):")
        abs_space = _safe_get(ptz_spaces, "Absolute")
        rel_space = _safe_get(ptz_spaces, "Relative")
        cont_space = _safe_get(ptz_spaces, "Continuous")
        if abs_space is not None:
            _print_range("Absolute", abs_space)
        if rel_space is not None:
            _print_range("Relative", rel_space)
        if cont_space is not None:
            _print_range("Continuous", cont_space)
        print(
            "\n(Ghi chú: Relative/Continuous thường là bước tương đối / vận tốc, "
            "không phải 'góc tối đa' cho AbsoluteMove.)"
        )
    else:
        print(
            "(Camera không trả PTZSpaces — nhiều EZVIZ/Hikvision chỉ dùng PanTiltLimits.)\n"
        )

    pl = _safe_get(cfg, "PanTiltLimits")
    if pl is not None:
        print("Giới hạn pan/tilt (PanTiltLimits):")
        rng = _safe_get(pl, "Range")
        if rng is not None:
            _print_range("Range", rng)
        else:
            _print_range("PanTiltLimits", pl)

    if ptz_spaces is not None:
        vel_hint = describe_velocity_and_relative_spaces(ptz_spaces)
        if vel_hint:
            print("\nTham khảo từ camera (velocity/relative):")
            print(vel_hint)

    try:
        pmin, pmax, tmin, tmax, src = extract_pan_tilt_ranges(
            cfg, ptz=ptz, ptz_cfg_token=ptz_cfg_token
        )
        print(
            f"\nTóm tắt cho AbsoluteMove ({src}): "
            f"pan [{pmin}, {pmax}], tilt [{tmin}, {tmax}]"
        )
    except RuntimeError as e:
        print("\n(!) Không suy ra được dải pan/tilt — in dump để đối chiếu firmware:")
        debug_dump_ptz_configuration(cfg, "GetConfiguration")
        opts = get_ptz_configuration_options(ptz, ptz_cfg_token)
        if opts is not None:
            debug_dump_ptz_configuration(opts, "GetConfigurationOptions")
        else:
            print("  (GetConfigurationOptions không gọi được hoặc không hỗ trợ.)")
        if _get_env("PTZ_DEBUG", "").lower() not in ("1", "true", "yes"):
            print(
                "\nGợi ý: bật PTZ_DEBUG=1 nếu cần thêm chi tiết; "
                "hoặc dùng ContinuousMove (ptz_wasd.py) nếu camera không công bố giới hạn qua ONVIF."
            )
        print(f"\n(Thông tin kỹ thuật) {e}")
        # Không raise để tránh chương trình dừng; vẫn có thể in được status phía dưới.

    # Thêm: in Current status nếu camera cung cấp
    try:
        status = ptz.GetStatus({"ProfileToken": profile_token})
        pos = _safe_get(status, "Position")
        pan_tilt = _safe_get(pos, "PanTilt") if pos is not None else None
        zoom = _safe_get(pos, "Zoom") if pos is not None else None
        print("\nVị trí hiện tại (nếu có):")
        print(f"- PanTilt: {pan_tilt}")
        print(f"- Zoom: {zoom}")
    except Exception:
        pass


if __name__ == "__main__":
    main()

