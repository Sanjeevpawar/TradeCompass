from datetime import datetime
from data.full_year_reconstruction import next_weekly_expiry, parse_timestamp


def test_epoch_timestamp_is_converted_to_ist():
    assert parse_timestamp("1788234300").isoformat().endswith("+05:30")


def test_iso_timestamp_is_converted_to_ist():
    assert parse_timestamp("2026-09-01T09:15:00+05:30").hour == 9


def test_tuesday_before_expiry_rolls_to_next_week():
    ts = datetime.fromisoformat("2026-09-01T09:15:00+05:30")
    assert next_weekly_expiry(ts).isoformat() == "2026-09-08"


def test_tuesday_after_expiry_rolls_two_weeks_forward_for_code_1():
    ts = datetime.fromisoformat("2026-09-01T15:30:00+05:30")
    assert next_weekly_expiry(ts).isoformat() == "2026-09-08"
