from analysis.v2.option_chain_intelligence import build_snapshot


def row(ts, option_type, strike, oi, iv=15):
    return {
        "timestamp": ts,
        "expiry": "2026-09-22",
        "strike": strike,
        "option_type": option_type,
        "open": 100,
        "high": 105,
        "low": 95,
        "close": 100,
        "iv": iv,
        "volume": 1000,
        "oi": oi,
        "spot": 24000,
        "identity_status": "DERIVED",
    }


def test_ce_pe_labels_are_normalized():
    rows = [
        row("2026-09-01T09:15:00+05:30", "CE", 24000, 1000),
        row("2026-09-01T09:15:00+05:30", "PE", 24000, 2000),
    ]
    snap = build_snapshot(rows)
    assert snap.call_contracts == 1
    assert snap.put_contracts == 1
    assert snap.common_strikes == 1
    assert snap.pcr_oi == 2.0


def test_call_put_labels_still_work():
    rows = [
        row("2026-09-01T09:15:00+05:30", "CALL", 24000, 1000),
        row("2026-09-01T09:15:00+05:30", "PUT", 24000, 2000),
    ]
    snap = build_snapshot(rows)
    assert snap.call_contracts == 1
    assert snap.put_contracts == 1
    assert snap.pcr_oi == 2.0
