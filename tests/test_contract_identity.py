from datetime import date

from data.contract_identity import black_scholes_delta, resolve_expiry, time_to_expiry_years


def test_dhan_next_weekly_expiry_for_sep_1_2026():
    r = resolve_expiry("2026-09-01T10:00:00+05:30", expiry_flag="WEEK", expiry_code=1)
    assert r.expiry == date(2026, 9, 8)
    assert r.confidence == "MEDIUM"


def test_after_expiry_rolls_current_contract_forward():
    r = resolve_expiry("2026-09-01T15:35:00+05:30", expiry_flag="WEEK", expiry_code=0)
    assert r.expiry == date(2026, 9, 8)


def test_nse_holiday_tuesday_shifts_nifty_expiry_to_previous_trading_day():
    # 31-Mar-2026 is an NSE trading holiday, so the NIFTY Tuesday expiry is
    # shifted to Monday 30-Mar-2026.
    current = resolve_expiry("2026-03-30T10:00:00+05:30", expiry_flag="WEEK", expiry_code=0)
    following = resolve_expiry("2026-03-30T10:00:00+05:30", expiry_flag="WEEK", expiry_code=1)
    assert current.expiry == date(2026, 3, 30)
    assert following.expiry == date(2026, 4, 7)


def test_after_shifted_holiday_expiry_rolls_to_next_week():
    # On the holiday itself the shifted Monday contract is already expired;
    # expiryCode 0 therefore resolves to the next Tuesday expiry.
    r = resolve_expiry("2026-03-31T10:00:00+05:30", expiry_flag="WEEK", expiry_code=0)
    assert r.expiry == date(2026, 4, 7)


def test_explicit_holiday_override_is_respected():
    # Explicit calendars remain supported for future historical windows.
    r = resolve_expiry(
        "2026-09-01T10:00:00+05:30",
        expiry_flag="WEEK",
        expiry_code=1,
        holidays=["2026-09-08"],
    )
    assert r.expiry == date(2026, 9, 7)


def test_black_scholes_call_delta_is_bounded():
    d = black_scholes_delta(spot=24000, strike=24000, iv_percent=15, time_to_expiry_years=7/365, option_type="CE")
    assert d is not None
    assert 0.45 < d < 0.60


def test_put_delta_is_negative():
    d = black_scholes_delta(spot=24000, strike=24000, iv_percent=15, time_to_expiry_years=7/365, option_type="PE")
    assert d is not None
    assert -0.60 < d < -0.45


def test_time_to_expiry_never_negative():
    assert time_to_expiry_years("2026-09-02T10:00:00+05:30", date(2026, 9, 1)) == 0.0
