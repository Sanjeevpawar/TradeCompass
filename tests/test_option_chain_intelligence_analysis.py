from scripts.analyze_option_chain_intelligence import analyse, stats


def snap(**kw):
    base = {
        "coverage_complete": True,
        "identity_status": "DERIVED",
        "pcr_oi": 1.0,
        "call_peak_distance": -100.0,
        "put_peak_distance": -100.0,
        "call_delta_oi": 10.0,
        "put_delta_oi": -5.0,
        "atm_call_iv": 15.0,
        "atm_put_iv": 16.0,
        "atm_call_oi": 100.0,
        "atm_put_oi": 120.0,
        "common_strikes": 20,
    }
    base.update(kw)
    return base


def test_stats_basic():
    s = stats([1, 2, 3, 4, 5])
    assert s["count"] == 5
    assert s["median"] == 3
    assert s["min"] == 1
    assert s["max"] == 5


def test_analysis_is_descriptive_only():
    r = analyse([snap(), snap(pcr_oi=1.5, call_delta_oi=-10, put_delta_oi=20)], progress_every=100)
    assert r["status"] == "PASS"
    assert r["snapshot_count"] == 2
    assert r["coverage_incomplete_snapshots"] == 0
    assert r["numeric_summary"]["pcr_oi"]["median"] == 1.25
    assert "trading" not in str(r).lower() or "trading rule" in str(r).lower()


def test_extreme_pcr_is_warning_not_a_signal():
    r = analyse([snap(pcr_oi=12.0)], progress_every=100)
    assert r["status"] == "PASS_WITH_WARNINGS"
    assert any("PCR" in w for w in r["warnings"])


def test_incomplete_coverage_is_reported():
    r = analyse([snap(coverage_complete=False)], progress_every=100)
    assert r["coverage_incomplete_snapshots"] == 1


def test_unknown_identity_is_reported():
    r = analyse([snap(identity_status="UNKNOWN")], progress_every=100)
    assert r["identity"]["UNKNOWN"] == 1
