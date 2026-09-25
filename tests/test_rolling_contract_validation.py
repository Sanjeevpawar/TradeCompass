from data.rolling_contract_validation import (
    validate_rolling_expiry,
    validate_underlying_alignment,
    validate_call_put_identity,
)


def row(ts, expiry, dte, strike="24050", spot="24042.55", opt="CE"):
    return {
        "timestamp": ts,
        "derived_expiry": expiry,
        "dte_days": str(dte),
        "strike": strike,
        "spot": spot,
        "option_type": opt,
    }


def test_expiry_segments_allow_dte_reset():
    rows = [
        row("2026-09-01T09:15:00+05:30", "2026-09-08", 7),
        row("2026-09-01T15:25:00+05:30", "2026-09-08", 7),
        row("2026-09-01T15:30:00+05:30", "2026-09-15", 14),
        row("2026-09-01T15:35:00+05:30", "2026-09-15", 14),
    ]
    result = validate_rolling_expiry(rows)
    assert result["pass"] is True
    assert [s["expiry"] for s in result["segments"]] == ["2026-09-08", "2026-09-15"]


def test_dte_increase_inside_same_expiry_fails():
    rows = [
        row("2026-09-01T09:15:00+05:30", "2026-09-08", 7),
        row("2026-09-01T09:20:00+05:30", "2026-09-08", 8),
    ]
    result = validate_rolling_expiry(rows)
    assert result["pass"] is False


def test_call_put_identity_matches():
    calls = [row("2026-09-01T09:15:00+05:30", "2026-09-08", 7, opt="CE")]
    puts = [row("2026-09-01T09:15:00+05:30", "2026-09-08", 7, opt="PE")]
    assert validate_call_put_identity(calls, puts)["pass"] is True


def test_missing_underlying_is_excluded_not_fabricated():
    options = [
        row("2026-09-01T09:15:00+05:30", "2026-09-08", 7),
        row("2026-09-01T15:30:00+05:30", "2026-09-08", 7),
    ]
    underlying = [{
        "timestamp": "2026-09-01T09:15:00+05:30",
        "close": "24042.55",
    }]
    result = validate_underlying_alignment(options, underlying)
    assert result["pass"] is True
    assert len(result["missing_timestamps"]) == 1


def test_spot_difference_is_warning():
    options = [row("2026-09-01T09:15:00+05:30", "2026-09-08", 7, spot="24050")]
    underlying = [{
        "timestamp": "2026-09-01T09:15:00+05:30",
        "close": "24045",
    }]
    result = validate_underlying_alignment(options, underlying)
    assert result["pass"] is True
    assert len(result["spot_warnings"]) == 1
