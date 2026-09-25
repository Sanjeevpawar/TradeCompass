from analysis.v2.option_chain_intelligence import build_historical_snapshots, build_snapshot


def row(ts, expiry, strike, typ, oi, iv=15, spot=24000, volume=1000, close=100):
    return {
        "timestamp": ts,
        "expiry": expiry,
        "strike": strike,
        "option_type": typ,
        "oi": oi,
        "iv": iv,
        "spot": spot,
        "volume": volume,
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "identity_status": "DERIVED",
    }


def test_pcr_uses_common_strikes_only():
    rows = [
        row("09:15", "2026-09-22", 23900, "CALL", 10),
        row("09:15", "2026-09-22", 24000, "CALL", 20),
        row("09:15", "2026-09-22", 24100, "CALL", 30),
        row("09:15", "2026-09-22", 23900, "PUT", 30),
        row("09:15", "2026-09-22", 24000, "PUT", 40),
        row("09:15", "2026-09-22", 24200, "PUT", 999),  # unmatched edge
    ]
    s = build_snapshot(rows, timestamp="09:15", spot=24000)
    assert s.common_strikes == 2
    assert s.call_oi == 30
    assert s.put_oi == 70
    assert s.pcr_oi == 70 / 30
    assert not s.coverage_complete


def test_peak_oi_and_distance_are_reported():
    rows = [
        row("09:15", "2026-09-22", 23900, "CALL", 10),
        row("09:15", "2026-09-22", 24100, "CALL", 100),
        row("09:15", "2026-09-22", 23900, "PUT", 120),
        row("09:15", "2026-09-22", 24100, "PUT", 20),
    ]
    s = build_snapshot(rows, timestamp="09:15", spot=24000)
    assert s.call_peak_strike == 24100
    assert s.put_peak_strike == 23900
    assert s.call_peak_distance == -100
    assert s.put_peak_distance == -100


def test_delta_oi_uses_same_fixed_contract_only():
    rows = [
        row("09:15", "2026-09-22", 24000, "CALL", 100),
        row("09:15", "2026-09-22", 24000, "PUT", 200),
        row("09:20", "2026-09-22", 24000, "CALL", 130),
        row("09:20", "2026-09-22", 24000, "PUT", 170),
        row("09:20", "2026-09-29", 24000, "CALL", 999),
    ]
    snapshots = build_historical_snapshots(rows)
    assert snapshots[0]["call_delta_oi"] is None
    assert snapshots[1]["call_delta_oi"] == 30
    assert snapshots[1]["put_delta_oi"] == -30


def test_duplicate_boundary_rows_do_not_double_count():
    base = row("09:15", "2026-09-22", 24000, "CALL", 100)
    rows = [base, dict(base, source_from_date="a"), row("09:15", "2026-09-22", 24000, "PUT", 200)]
    s = build_snapshot(rows, timestamp="09:15", spot=24000)
    assert s.call_contracts == 1
    assert s.put_contracts == 1
    assert s.call_oi == 100
    assert s.put_oi == 200


def test_identity_status_is_preserved_and_not_repaired():
    rows = [row("09:15", "2026-10-21", 24000, "CALL", 100)]
    s = build_snapshot(rows, timestamp="09:15", spot=24000)
    assert s.identity_status == "DERIVED"
