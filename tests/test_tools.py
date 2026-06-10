from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.tools import clear_tle_cache, compute_position_from_tle, get_latest_tle, resolve_norad_id
from src.utils import parse_prediction_offset_minutes, parse_tle_lines

ISS_TLE = """ISS (ZARYA)
1 25544U 98067A   24001.00000000  .00016717  00000+0  10270-3 0  9001
2 25544  51.6416  24.2445 0005817  92.3437  28.4015 15.50000000  1000
"""


class FakeSpaceTrackClient:
    def __init__(self):
        self.calls = 0

    def gp(self, **kwargs):
        self.calls += 1
        assert kwargs["norad_cat_id"] == 25544
        assert kwargs["format"] == "tle"
        return ISS_TLE


def test_resolve_norad_id_supports_common_names():
    assert resolve_norad_id("国际空间站") == 25544
    assert resolve_norad_id("ISS") == 25544
    assert resolve_norad_id("哈勃") == 20580


def test_get_latest_tle_uses_client_and_cache():
    clear_tle_cache()
    client = FakeSpaceTrackClient()

    first = get_latest_tle("iss", client=client)
    second = get_latest_tle("iss", client=client)

    assert first == ISS_TLE
    assert second == ISS_TLE
    assert client.calls == 1


def test_parse_tle_lines_accepts_three_line_tle():
    line1, line2 = parse_tle_lines(ISS_TLE)

    assert line1.startswith("1 25544")
    assert line2.startswith("2 25544")


def test_parse_prediction_offset_minutes():
    assert parse_prediction_offset_minutes("30 分钟后的位置") == 30
    assert parse_prediction_offset_minutes("2 hours later") == 120
    assert parse_prediction_offset_minutes("现在在哪里") is None


def test_compute_position_from_tle_returns_reasonable_iss_position():
    pytest.importorskip("sgp4")

    position = compute_position_from_tle(
        ISS_TLE,
        at_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    assert "error" not in position
    assert -52 <= position["latitude"] <= 52
    assert -180 <= position["longitude"] <= 180
    assert 350 <= position["altitude_km"] <= 500
