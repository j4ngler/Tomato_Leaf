# -*- coding: utf-8 -*-
"""Tiện ích chung cho ONVIF PTZ (onvif-zeep)."""
from typing import Any, Iterable, List, Optional, Tuple

# Tên thuộc tính thường gặp (zeep giữ PascalCase; một số bản build khác nhau)
_PAN_TILT_LIMITS_NAMES = ("PanTiltLimits", "pan_tilt_limits")
_PTZ_SPACES_NAMES = ("PTZSpaces", "ptz_spaces", "Spaces", "spaces")


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    try:
        return getattr(obj, attr)
    except Exception:
        return default


def _first_attr(obj: Any, names: Tuple[str, ...]) -> Any:
    for n in names:
        v = _safe_get(obj, n)
        if v is not None:
            return v
    return None


def ptz_configuration_token(profile: Any) -> str:
    """Token cấu hình PTZ — dùng cho GetConfiguration (ONVIF 2.x)."""
    ptz_cfg = _safe_get(profile, "PTZConfiguration")
    if ptz_cfg is None:
        raise RuntimeError(
            "Profile không có PTZConfiguration (không phải profile PTZ hoặc camera chưa gán PTZ)."
        )
    tok = _safe_get(ptz_cfg, "token")
    if tok is None:
        raise RuntimeError("PTZConfiguration không có token.")
    if isinstance(tok, (list, tuple, dict)):
        raise RuntimeError(f"PTZConfiguration.token không hợp lệ: {tok!r}")
    return str(tok)


def select_profile_with_ptz(profiles: List[Any]) -> Any:
    """Chọn profile đầu tiên có PTZConfiguration."""
    if not profiles:
        raise RuntimeError("Danh sách profiles rỗng.")
    last_err: Optional[Exception] = None
    for p in profiles:
        try:
            ptz_configuration_token(p)
            return p
        except RuntimeError as e:
            last_err = e
            continue
    raise RuntimeError(
        "Không profile nào có PTZConfiguration. Kiểm tra camera có PTZ và ONVIF."
    ) from last_err


def get_ptz_configuration(ptz: Any, profile: Any) -> Any:
    """Gọi GetConfiguration đúng tham số PTZConfigurationToken."""
    token = ptz_configuration_token(profile)
    return ptz.GetConfiguration({"PTZConfigurationToken": token})


def _ranges_from_xy_container(obj: Any) -> Optional[Tuple[float, float, float, float]]:
    """Đọc XRange/YRange (Min/Max) từ một block ONVIF."""
    if obj is None:
        return None
    xr = _safe_get(obj, "XRange")
    yr = _safe_get(obj, "YRange")
    if xr is None or yr is None:
        return None
    xmin, xmax = _safe_get(xr, "Min"), _safe_get(xr, "Max")
    ymin, ymax = _safe_get(yr, "Min"), _safe_get(yr, "Max")
    if xmin is None or xmax is None or ymin is None or ymax is None:
        return None
    return float(xmin), float(xmax), float(ymin), float(ymax)


def _iter_maybe_sequence(x: Any) -> Iterable[Any]:
    if x is None:
        return
    if isinstance(x, (list, tuple)):
        for i in x:
            yield i
    else:
        yield x


def _try_absolute_position_spaces_only(
    ptz_spaces: Any,
) -> Optional[Tuple[float, float, float, float, str]]:
    """
    Chỉ không gian VỊ TRÍ tuyệt đối (dùng cho AbsoluteMove).
    KHÔNG dùng Continuous/Relative/Velocity: chúng là vận tốc hoặc bước tương đối,
    dải -1..1 không phải 'góc quay tối đa' theo nghĩa độ.
    """
    if ptz_spaces is None:
        return None

    block = _safe_get(ptz_spaces, "Absolute")
    r = _ranges_from_xy_container(block)
    if r is not None:
        return (*r, "PTZSpaces.Absolute")

    seq = _safe_get(ptz_spaces, "AbsolutePanTiltPositionSpace")
    for item in _iter_maybe_sequence(seq):
        r = _ranges_from_xy_container(item)
        if r is not None:
            return (*r, "PTZSpaces.AbsolutePanTiltPositionSpace")

    return None


def describe_velocity_and_relative_spaces(ptz_spaces: Any) -> Optional[str]:
    """Thông tin tham khảo: dải -1..1 thường là normalized velocity, không phải giới hạn góc."""
    if ptz_spaces is None:
        return None
    parts: List[str] = []
    for key in (
        "Continuous",
        "ContinuousPanTiltVelocitySpace",
        "Relative",
        "RelativePanTiltTranslationSpace",
    ):
        block_or_seq = _safe_get(ptz_spaces, key)
        if block_or_seq is None:
            continue
        for item in _iter_maybe_sequence(block_or_seq):
            r = _ranges_from_xy_container(item)
            if r is not None:
                parts.append(f"{key}: pan/tilt range {r[0]}..{r[1]} / {r[2]}..{r[3]} (thường là velocity/relative, không phải góc tuyệt đối)")
                break
    if not parts:
        return None
    return "\n".join(parts)


def _try_pan_tilt_limits(pl: Any) -> Optional[Tuple[float, float, float, float, str]]:
    if pl is None:
        return None
    rng = _safe_get(pl, "Range")
    for candidate in _iter_maybe_sequence(rng):
        r = _ranges_from_xy_container(candidate)
        if r is not None:
            return (*r, "PanTiltLimits.Range")
    r = _ranges_from_xy_container(pl)
    if r is not None:
        return (*r, "PanTiltLimits (trực tiếp)")
    return None


def _iter_public_named(obj: Any) -> Iterable[Tuple[str, Any]]:
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            v = getattr(obj, name)
        except Exception:
            continue
        if callable(v):
            continue
        yield name, v


def _is_velocity_or_relative_branch(attr_name: str) -> bool:
    """Không coi nhánh này là giới hạn góc cho AbsoluteMove."""
    if not attr_name:
        return False
    lower = attr_name.lower()
    if "velocity" in lower:
        return True
    if attr_name in (
        "Continuous",
        "Relative",
        "ContinuousPanTiltVelocitySpace",
        "RelativePanTiltTranslationSpace",
        "RelativePanTiltTranslationLimits",
    ):
        return True
    return False


def _dfs_find_xy_ranges(
    obj: Any,
    depth: int = 0,
    seen: Optional[set] = None,
    parent_attr: str = "",
) -> Optional[Tuple[float, float, float, float]]:
    """Tìm XRange/YRange trong cây; bỏ qua nhánh Continuous/Velocity để tránh nhầm -1..1."""
    if seen is None:
        seen = set()
    if depth > 18 or obj is None:
        return None
    if isinstance(obj, (str, bytes, int, float, bool)):
        return None
    tname = type(obj).__name__
    if "Element" in tname or "lxml" in str(type(obj)):
        return None
    oid = id(obj)
    if oid in seen:
        return None
    seen.add(oid)

    r = _ranges_from_xy_container(obj)
    if r is not None and not _is_velocity_or_relative_branch(parent_attr):
        return r

    if isinstance(obj, (list, tuple)):
        for item in obj:
            r = _dfs_find_xy_ranges(item, depth + 1, seen, parent_attr=parent_attr)
            if r is not None:
                return r
    elif isinstance(obj, dict):
        for v in obj.values():
            r = _dfs_find_xy_ranges(v, depth + 1, seen, parent_attr=parent_attr)
            if r is not None:
                return r
    else:
        for name, v in _iter_public_named(obj):
            r = _dfs_find_xy_ranges(
                v, depth + 1, seen, parent_attr=name
            )
            if r is not None:
                return r
    return None


def get_ptz_configuration_options(ptz: Any, ptz_cfg_token: str) -> Any:
    """Gọi GetConfigurationOptions (tham số có thể khác nhau giữa firmware)."""
    for params in (
        {"PTZConfigurationToken": ptz_cfg_token},
        {"ConfigurationToken": ptz_cfg_token},
    ):
        try:
            return ptz.GetConfigurationOptions(params)
        except Exception:
            continue
    return None


def _extract_from_object(obj: Any, source_label: str) -> Optional[Tuple[float, float, float, float, str]]:
    if obj is None:
        return None
    ps = _first_attr(obj, _PTZ_SPACES_NAMES)
    got = _try_absolute_position_spaces_only(ps)
    if got is not None:
        return (*got[:4], f"{source_label}.{got[4]}")
    pl = _first_attr(obj, _PAN_TILT_LIMITS_NAMES)
    got = _try_pan_tilt_limits(pl)
    if got is not None:
        return got
    r = _dfs_find_xy_ranges(obj, parent_attr="")
    if r is not None:
        return (*r, f"DFS({source_label})")
    return None


def extract_pan_tilt_ranges(
    cfg: Any,
    ptz: Any = None,
    ptz_cfg_token: Optional[str] = None,
) -> Tuple[float, float, float, float, str]:
    """
    Lấy (pan_min, pan_max, tilt_min, tilt_max) và mô tả nguồn.
    Thử GetConfiguration, sau đó DFS, sau đó GetConfigurationOptions (nếu có ptz + token).
    """
    got = _extract_from_object(cfg, "GetConfiguration")
    if got is not None:
        return got

    if ptz is not None and ptz_cfg_token:
        opts = get_ptz_configuration_options(ptz, ptz_cfg_token)
        if opts is not None:
            got = _extract_from_object(opts, "GetConfigurationOptions")
            if got is not None:
                return got

    raise RuntimeError(
        "Không đọc được giới hạn VỊ TRÍ tuyệt đối (Absolute) từ ONVIF. "
        "Nhiều EZVIZ chỉ công bố Continuous/Velocity (-1..1) — đó là vận tốc, không phải 'bao nhiêu độ'. "
        "Dùng lập lịch ContinuousMove (nhích theo giây) hoặc xem dump trong ptz_limits.py."
    )


def debug_dump_ptz_configuration(cfg: Any, title: str = "GetConfiguration") -> None:
    """In các thuộc tính công khai của object (hỗ trợ gỡ lỗi)."""
    names = sorted(
        n
        for n in dir(cfg)
        if not n.startswith("_") and not callable(getattr(cfg, n, None))
    )
    print(f"--- PTZ_DEBUG: thuộc tính {title} ---")
    for name in names:
        try:
            val = getattr(cfg, name)
        except Exception:
            continue
        print(f"  {name}: {type(val).__name__} = {val!r}")
    print("--- hết dump ---")


if __name__ == "__main__":
    print(
        "Module tiện ích — không chạy trực tiếp.\n"
        "Dùng: python camera_control/ptz_limits.py"
    )
