from data.fixed_contract_reconstruction import reconstruct_fixed_contracts


def row(ts, expiry="2026-09-15", strike="24000", option_type="CE", close="100"):
    return {
        "timestamp": ts,
        "derived_expiry": expiry,
        "strike": strike,
        "option_type": option_type,
        "open": close,
        "high": str(float(close) + 2),
        "low": str(float(close) - 2),
        "close": close,
        "spot": "24000",
        "identity_status": "DERIVED",
    }


def test_same_contract_is_kept_together():
    rows = [
        row("2026-09-01T09:15:00+05:30"),
        row("2026-09-01T09:20:00+05:30", close="101"),
        row("2026-09-01T09:25:00+05:30", close="102"),
    ]
    out, report = reconstruct_fixed_contracts(rows, expected_interval_minutes=5)
    assert len(out) == 3
    assert report["contracts"]["count"] == 1
    assert report["contracts"]["continuity"] == {"CONTINUOUS": 1}
    assert all(r["contract_key"] == "2026-09-15|24000|CE" for r in out)
    assert all(r["reconstruction_eligible"] for r in out)


def test_strike_change_creates_two_fixed_contracts():
    rows = [
        row("2026-09-01T09:15:00+05:30", strike="24000"),
        row("2026-09-01T09:20:00+05:30", strike="24050"),
    ]
    out, report = reconstruct_fixed_contracts(rows)
    assert len(out) == 2
    assert report["contracts"]["count"] == 2
    assert {r["contract_key"] for r in out} == {
        "2026-09-15|24000|CE",
        "2026-09-15|24050|CE",
    }


def test_same_day_gap_is_not_filled():
    rows = [
        row("2026-09-01T09:15:00+05:30"),
        row("2026-09-01T09:25:00+05:30"),
    ]
    out, report = reconstruct_fixed_contracts(rows)
    assert report["contracts"]["continuity"] == {"GAPPED": 1}
    assert out[0]["same_day_gap_count"] == 1
    assert out[0]["reconstruction_eligible"] is False


def test_overnight_gap_is_not_marked_missing():
    rows = [
        row("2026-09-01T15:25:00+05:30"),
        row("2026-09-02T09:15:00+05:30"),
    ]
    out, report = reconstruct_fixed_contracts(rows)
    assert report["contracts"]["continuity"] == {"CONTINUOUS": 1}
    assert out[0]["same_day_gap_count"] == 0


def test_expiry_change_creates_distinct_contracts():
    rows = [
        row("2026-09-01T09:15:00+05:30", expiry="2026-09-08"),
        row("2026-09-01T09:20:00+05:30", expiry="2026-09-15"),
    ]
    out, report = reconstruct_fixed_contracts(rows)
    assert report["contracts"]["count"] == 2
    assert {r["contract_key"] for r in out} == {
        "2026-09-08|24000|CE",
        "2026-09-15|24000|CE",
    }


def test_call_and_put_are_distinct_contracts():
    rows = [
        row("2026-09-01T09:15:00+05:30", option_type="CE"),
        row("2026-09-01T09:15:00+05:30", option_type="PE"),
    ]
    out, report = reconstruct_fixed_contracts(rows)
    assert report["contracts"]["count"] == 2
    assert {r["contract_key"] for r in out} == {
        "2026-09-15|24000|CE",
        "2026-09-15|24000|PE",
    }


def test_derived_identity_stays_explicit():
    rows = [row("2026-09-01T09:15:00+05:30")]
    out, _ = reconstruct_fixed_contracts(rows)
    assert out[0]["contract_identity_status"] == "DERIVED"
    assert out[0]["reconstruction_eligible"] is False  # singleton, not identity rejection
