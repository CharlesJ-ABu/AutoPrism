import pytest
from fastapi import HTTPException

from app.api.v1.system import (
    _parse_daily_time,
    _parse_interval,
    _require_reset_confirmation,
)


def test_daily_time_validation() -> None:
    assert _parse_daily_time("08:30") == (8, 30)
    with pytest.raises(ValueError):
        _parse_daily_time("25:00")
    with pytest.raises(ValueError):
        _parse_daily_time("invalid")


def test_interval_validation() -> None:
    assert _parse_interval("15") == 15
    for invalid in ("0", "-1", "10081", "hourly"):
        with pytest.raises(ValueError):
            _parse_interval(invalid)


def test_reset_requires_exact_confirmation() -> None:
    _require_reset_confirmation("l1", "RESET-L1")
    with pytest.raises(HTTPException) as exc_info:
        _require_reset_confirmation("l1", None)
    assert exc_info.value.status_code == 409
