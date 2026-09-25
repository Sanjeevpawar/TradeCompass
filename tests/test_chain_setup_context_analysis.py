
import json
from scripts.analyze_chain_setup_context import analyse

def test_chain_setup_analysis_preserves_same_time_evidence(tmp_path):
    src=tmp_path/"in.json"; out=tmp_path/"out.json"
    src.write_text(json.dumps({"snapshots_data":[
        {"timestamp":"t1","coverage_complete":True,"identity_status":"DERIVED",
         "pcr_oi":1.1,"call_delta_oi":20,"put_delta_oi":30,
         "call_oi":100,"put_oi":120},
        {"timestamp":"t2","coverage_complete":False,"identity_status":"DERIVED",
         "pcr_oi":0.8,"call_delta_oi":10,"put_delta_oi":15,
         "call_oi":90,"put_oi":70}
    ]}),encoding="utf-8")
    r=analyse(src,out,progress_every=100)
    assert r["snapshots"] == 2
    assert r["coverage_incomplete"] == 1
    assert len(r["snapshot_records"]) == 2
    assert r["snapshot_records"][0]["timestamp"] == "t1"

def test_no_strategy_integration(tmp_path):
    src=tmp_path/"in.json"; out=tmp_path/"out.json"
    src.write_text(json.dumps({"snapshots_data":[]}),encoding="utf-8")
    r=analyse(src,out,progress_every=100)
    assert r["status"]=="PASS"
    assert r["snapshots"] == 0
    assert r["snapshot_records"] == []
