from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

from .utils import (
    ensure_utc,
    ecef_to_geodetic,
    gmst_from_julian_date,
    parse_tle_lines,
    teme_to_ecef_approx,
)

SATELLITE_NAME_TO_NORAD_ID: dict[str, int] = {
    "国际空间站": 25544,
    "空间站": 25544,
    "iss": 25544,
    "international space station": 25544,
    "哈勃": 20580,
    "哈勃望远镜": 20580,
    "hubble": 20580,
    "hubble space telescope": 20580,
    "天宫": 48274,
    "中国空间站": 48274,
    "tiangong": 48274,
}

_TLE_CACHE: dict[int, tuple[float, str]] = {}


def resolve_norad_id(satellite_name: str) -> int | None:
    """Resolve a common satellite name to a NORAD catalog id."""

    return SATELLITE_NAME_TO_NORAD_ID.get(satellite_name.strip().lower())


def extract_satellite_name(text: str) -> str:
    """Extract a supported satellite name from user text, defaulting to ISS."""

    normalized = text.lower()
    candidates = sorted(SATELLITE_NAME_TO_NORAD_ID, key=len, reverse=True)
    for candidate in candidates:
        if candidate in normalized:
            return candidate
    return "国际空间站"


def get_latest_tle(
    satellite_name: str,
    *,
    client: Any | None = None,
    cache_ttl_seconds: int = 3600,
    use_cache: bool = True,
) -> str:
    """Fetch the latest TLE for a satellite from Space-Track.

    The optional client argument is used by tests to avoid real API calls.
    """

    norad_id = resolve_norad_id(satellite_name)
    if not norad_id:
        return f"ERROR: 未知卫星: {satellite_name}"

    now = time.time()
    cached = _TLE_CACHE.get(norad_id)
    if use_cache and cached and now - cached[0] < cache_ttl_seconds:
        return cached[1]

    if client is None:
        _load_dotenv_if_available()
        username = os.getenv("SPACETRACK_USER")
        password = os.getenv("SPACETRACK_PASS")
        if not username or not password:
            return "ERROR: 缺少 SPACETRACK_USER 或 SPACETRACK_PASS 环境变量"

        try:
            from spacetrack import SpaceTrackClient
        except ImportError:
            return "ERROR: 未安装 spacetrack，请先运行 pip install -r requirements.txt"

        client = SpaceTrackClient(identity=username, password=password)

    try:
        tle = client.gp(
            norad_cat_id=norad_id,
            orderby="epoch desc",
            limit=1,
            format="tle",
        )
    except Exception as exc:  # pragma: no cover - network/client dependent
        return f"ERROR: Space-Track 查询失败: {exc}"

    if not isinstance(tle, str) or not tle.strip():
        return f"ERROR: Space-Track 未返回 {satellite_name} 的 TLE 数据"

    _TLE_CACHE[norad_id] = (now, tle)
    return tle


def compute_position_from_tle(tle_str: str, at_time: datetime | None = None) -> dict[str, Any]:
    """Compute geodetic latitude, longitude and altitude from a TLE using SGP4."""

    if tle_str.startswith("ERROR:"):
        return {"error": tle_str.removeprefix("ERROR:").strip()}

    try:
        line1, line2 = parse_tle_lines(tle_str)
    except ValueError as exc:
        return {"error": str(exc)}

    try:
        from sgp4.api import Satrec, jday
    except ImportError:
        return {"error": "未安装 sgp4，请先运行 pip install -r requirements.txt"}

    timestamp = ensure_utc(at_time)
    seconds = timestamp.second + timestamp.microsecond / 1_000_000
    jd, fr = jday(
        timestamp.year,
        timestamp.month,
        timestamp.day,
        timestamp.hour,
        timestamp.minute,
        seconds,
    )

    satellite = Satrec.twoline2rv(line1, line2)
    error_code, position_teme_km, velocity_km_s = satellite.sgp4(jd, fr)
    if error_code != 0:
        return {"error": f"轨道计算失败，SGP4 错误码 {error_code}"}

    gmst = gmst_from_julian_date(jd + fr)
    x_km, y_km, z_km = teme_to_ecef_approx(position_teme_km, gmst)
    latitude, longitude, altitude_km = ecef_to_geodetic(x_km, y_km, z_km)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "altitude_km": altitude_km,
        "timestamp_utc": timestamp.isoformat(),
        "velocity_km_s": tuple(velocity_km_s),
    }


def clear_tle_cache() -> None:
    """Clear the in-memory TLE cache. Primarily useful for tests."""

    _TLE_CACHE.clear()


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()
