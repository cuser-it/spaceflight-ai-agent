from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

EARTH_EQUATORIAL_RADIUS_KM = 6378.137
EARTH_FLATTENING = 1 / 298.257223563


def ensure_utc(dt: datetime | None = None) -> datetime:
    """Return a timezone-aware UTC datetime."""

    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_tle_lines(tle_str: str) -> tuple[str, str]:
    """Extract line 1 and line 2 from a two-line or three-line TLE string."""

    lines = [line.strip() for line in tle_str.strip().splitlines() if line.strip()]
    tle_lines = [line for line in lines if line.startswith("1 ") or line.startswith("2 ")]
    if len(tle_lines) < 2:
        raise ValueError("无效的 TLE 格式：需要包含以 '1 ' 和 '2 ' 开头的两行")
    return tle_lines[0], tle_lines[1]


def parse_prediction_offset_minutes(text: str) -> int | None:
    """Parse a simple future offset such as '30 分钟后' or '2 hours later'."""

    normalized = text.lower()
    minute_match = re.search(r"(\d+)\s*(分钟|minute|minutes|min|mins)\s*(后|later)?", normalized)
    if minute_match:
        return int(minute_match.group(1))

    hour_match = re.search(r"(\d+)\s*(小时|hour|hours|hr|hrs|h)\s*(后|later)?", normalized)
    if hour_match:
        return int(hour_match.group(1)) * 60

    return None


def gmst_from_julian_date(julian_date: float) -> float:
    """Compute Greenwich mean sidereal time in radians."""

    centuries = (julian_date - 2451545.0) / 36525.0
    gmst_degrees = (
        280.46061837
        + 360.98564736629 * (julian_date - 2451545.0)
        + 0.000387933 * centuries**2
        - centuries**3 / 38710000.0
    )
    return math.radians(gmst_degrees % 360.0)


def teme_to_ecef_approx(position_km: Iterable[float], gmst_radians: float) -> tuple[float, float, float]:
    """Approximate TEME to ECEF with a GMST z-axis rotation.

    This is sufficient for a demo and unit tests. Production mission analysis
    should use a full Earth orientation model.
    """

    x, y, z = position_km
    cos_theta = math.cos(gmst_radians)
    sin_theta = math.sin(gmst_radians)
    return (
        cos_theta * x + sin_theta * y,
        -sin_theta * x + cos_theta * y,
        z,
    )


def ecef_to_geodetic(x_km: float, y_km: float, z_km: float) -> tuple[float, float, float]:
    """Convert ECEF coordinates in km to WGS84 latitude, longitude and altitude."""

    semi_major = EARTH_EQUATORIAL_RADIUS_KM
    flattening = EARTH_FLATTENING
    eccentricity_squared = flattening * (2 - flattening)

    longitude = math.atan2(y_km, x_km)
    p = math.hypot(x_km, y_km)
    latitude = math.atan2(z_km, p * (1 - eccentricity_squared))

    for _ in range(8):
        sin_latitude = math.sin(latitude)
        radius = semi_major / math.sqrt(1 - eccentricity_squared * sin_latitude**2)
        altitude = p / max(math.cos(latitude), 1e-12) - radius
        latitude = math.atan2(z_km, p * (1 - eccentricity_squared * radius / (radius + altitude)))

    sin_latitude = math.sin(latitude)
    radius = semi_major / math.sqrt(1 - eccentricity_squared * sin_latitude**2)
    altitude = p / max(math.cos(latitude), 1e-12) - radius

    return math.degrees(latitude), normalize_longitude(math.degrees(longitude)), altitude


def normalize_longitude(longitude: float) -> float:
    """Normalize longitude to [-180, 180)."""

    return ((longitude + 180.0) % 360.0) - 180.0


def offset_datetime(minutes: int | None, base_time: datetime | None = None) -> datetime:
    """Return base UTC time plus an optional minute offset."""

    current = ensure_utc(base_time)
    if not minutes:
        return current
    return current + timedelta(minutes=minutes)
