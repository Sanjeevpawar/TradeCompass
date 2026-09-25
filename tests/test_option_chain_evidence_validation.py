
import json
from scripts.validate_option_chain_evidence import analyse


def test_phase_10_17_snapshots_data_is_used(tmp_path):
    src = tmp_path/"in.json"
    out = tmp_path/"out.json"
    src.write_text(json.dumps({
        "snapshots": 2,
        "snapshots_data": [
            {"timestamp":"t1","coverage_complete":True,"identity_status":"DERIVED",
             "pcr_oi":0.8,"call_delta_oi":10,"put_delta_oi":30},
            {"timestamp":"t2","coverage_complete":False,"identity_status":"DERIVED",
             "pcr_oi":1.2,"call_delta_oi":20,"put_delta_oi":40,
             "call_contracts":21,"put_contracts":20,"common_strikes":20,
             "call_only_strikes":1,"put_only_strikes":0}
        ]
    }), encoding="utf-8")
    r = analyse(src, out, progress_every=100)
    assert r["snapshots"] == 2
    assert r["coverage_incomplete"] == 1
    assert r["distributions"]["pcr_oi"]["median"] == 1.0
    assert r["distributions"]["call_delta_oi"]["median"] == 15.0
    assert r["distributions"]["put_delta_oi"]["median"] == 35.0


def test_missing_snapshot_records_is_explicit_error(tmp_path):
    src = tmp_path/"in.json"
    out = tmp_path/"out.json"
    src.write_text(json.dumps({"snapshots": 18665}), encoding="utf-8")
    try:
        analyse(src, out, progress_every=100)
    except ValueError as e:
        assert "snapshots_data" in str(e)
    else:
        raise AssertionError("Expected missing snapshot data to be rejected")


def test_no_strategy_integration(tmp_path):
    src = tmp_path/"in.json"
    out = tmp_path/"out.json"
    src.write_text(json.dumps({"snapshots_data":[]}), encoding="utf-8")
    r = analyse(src, out, progress_every=100)
    assert r["status"] == "INVALID"
