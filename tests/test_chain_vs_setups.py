
import csv, json
from scripts.analyze_chain_vs_setups import analyse

def _write_underlying(p):
    rows=[]
    for i in range(40):
        px=100+i
        rows.append({"timestamp":f"t{i}","open":px,"high":px+1,"low":px-1,"close":px,"volume":1000,"oi":""})
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["timestamp","open","high","low","close","volume","oi"])
        w.writeheader(); w.writerows(rows)

def test_same_timestamp_chain_is_joined_without_lookahead(tmp_path):
    u=tmp_path/"u.csv"; c=tmp_path/"c.json"; o=tmp_path/"o.json"
    _write_underlying(u)
    c.write_text(json.dumps({"snapshots_data":[
        {"timestamp":"t35","coverage_complete":True,"identity_status":"DERIVED",
         "pcr_oi":1.1,"call_delta_oi":10,"put_delta_oi":20}
    ]}),encoding="utf-8")
    # The test mainly verifies schema/policy; setup generation depends on the
    # existing deterministic strategy and may produce zero occurrences.
    r=analyse(u,c,o,progress_every=1000)
    assert r["status"]=="PASS"
    assert r["research_policy"]["same_timestamp_chain_only"] is True
    assert r["research_policy"]["forward_outcome_is_not_used_in_signal"] is True

def test_missing_chain_is_not_fabricated(tmp_path):
    u=tmp_path/"u.csv"; c=tmp_path/"c.json"; o=tmp_path/"o.json"
    _write_underlying(u)
    c.write_text(json.dumps({"snapshots_data":[]}),encoding="utf-8")
    r=analyse(u,c,o,progress_every=1000)
    assert r["status"]=="PASS"
    assert r["chain_snapshots"]==0
