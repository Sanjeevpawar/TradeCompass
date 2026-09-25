from backtesting.v2.engine import _has_full_horizon
from backtesting.v2.models import HistoricalOptionBar


def bar(i):
    return HistoricalOptionBar(str(i), "2026-09-15", 24000, "CE", 100, 101, 99, 100)


def test_full_horizon_requires_entry_plus_future_bars():
    series = [bar(i) for i in range(13)]
    assert _has_full_horizon(series, 0, 12) is True
    assert _has_full_horizon(series, 1, 12) is False


def test_short_series_is_not_accepted_for_full_horizon():
    series = [bar(i) for i in range(12)]
    assert _has_full_horizon(series, 0, 12) is False
