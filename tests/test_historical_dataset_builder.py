from data.historical_dataset_builder import OUTPUT_FIELDS, build_dataset


def option_row(ts, option_type="CE", expiry="2026-09-08", dte="7", delta="0.50"):
    return {
        "timestamp": ts,
        "timestamp_epoch": "1",
        "option_type": option_type,
        "open": "100", "high": "110", "low": "95", "close": "105",
        "iv": "15", "volume": "1000", "strike": "24000", "oi": "5000", "spot": "24010",
        "derived_expiry": expiry, "dte_days": dte, "time_to_expiry_years": "0.019",
        "model_delta": delta, "delta_source": "black_scholes_from_dhan_iv_spot_strike",
        "expiry_flag": "WEEK", "expiry_code": "1", "strike_mode": "ATM",
        "identity_method": "exchange_expiry_calendar_tuesday_regime",
        "identity_confidence": "MEDIUM",
        "identity_note": "derived",
    }


def underlying_row(ts):
    return {"timestamp": ts, "open": "24000", "high": "24020", "low": "23990", "close": "24010", "volume": "100000"}


def test_exact_timestamp_join_and_derived_identity():
    rows, report = build_dataset(
        [option_row("2026-09-01T09:15:00+05:30")],
        [option_row("2026-09-01T09:15:00+05:30", "PE", delta="-0.50")],
        [underlying_row("2026-09-01T09:15:00+05:30")],
    )
    assert len(rows) == 2
    assert all(r["timestamp_alignment"] == "EXACT" for r in rows)
    assert all(r["identity_status"] == "DERIVED" for r in rows)
    assert all(r["backtest_eligible"] is True for r in rows)
    assert report["backtest_gate"]["allowed"] is False


def test_missing_underlying_is_excluded_not_filled():
    rows, report = build_dataset(
        [option_row("2026-09-01T09:20:00+05:30")],
        [],
        [underlying_row("2026-09-01T09:15:00+05:30")],
    )
    assert len(rows) == 1
    assert rows[0]["timestamp_alignment"] == "MISSING"
    assert rows[0]["underlying_close"] is None
    assert rows[0]["backtest_eligible"] is False
    assert "missing_exact_underlying_timestamp" in rows[0]["eligibility_reason"]
    assert report["rows"]["excluded"] == 1


def test_missing_delta_is_excluded():
    row = option_row("2026-09-01T09:15:00+05:30", delta="")
    rows, _ = build_dataset([row], [], [underlying_row("2026-09-01T09:15:00+05:30")])
    assert rows[0]["backtest_eligible"] is False
    assert "missing_model_delta" in rows[0]["eligibility_reason"]


def test_output_schema_contains_underlying_and_option_fields():
    assert "underlying_close" in OUTPUT_FIELDS
    assert "option_open" in OUTPUT_FIELDS
    assert "derived_expiry" in OUTPUT_FIELDS
    assert "model_delta" in OUTPUT_FIELDS
    assert "identity_status" in OUTPUT_FIELDS
    assert "backtest_eligible" in OUTPUT_FIELDS
