
from __future__ import annotations
import json
from pathlib import Path
from statistics import median

INPUT=Path("data/dhan_history/reconstructed/option_chain_intelligence_1y.json")
OUTPUT=Path("data/dhan_history/reconstructed/option_chain_setup_analysis_1y.json")


def _num(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool)

def analyse(path=INPUT, output=OUTPUT, progress_every=1000):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    rows=data.get("snapshots_data")
    if not isinstance(rows,list):
        raise ValueError("Expected snapshots_data list in option-chain intelligence report")

    # This phase deliberately studies chain evidence only. It does not
    # infer BUY/SELL labels or alter the strategy.
    records=[]
    incomplete=0
    pcr=[]
    call_doi=[]
    put_doi=[]
    call_oi=[]
    put_oi=[]

    for i,row in enumerate(rows,1):
        if row.get("coverage_complete") is False:
            incomplete += 1

        for key,target in [
            ("pcr_oi",pcr),
            ("call_delta_oi",call_doi),
            ("put_delta_oi",put_doi),
            ("call_oi",call_oi),
            ("put_oi",put_oi),
        ]:
            v=row.get(key)
            if _num(v):
                target.append(float(v))

        # Preserve only evidence available in the chain snapshot.
        records.append({
            "timestamp":row.get("timestamp"),
            "identity_status":row.get("identity_status"),
            "coverage_complete":row.get("coverage_complete"),
            "pcr_oi":row.get("pcr_oi"),
            "call_delta_oi":row.get("call_delta_oi"),
            "put_delta_oi":row.get("put_delta_oi"),
            "call_oi":row.get("call_oi"),
            "put_oi":row.get("put_oi"),
            "call_peak_strike":row.get("call_peak_strike"),
            "put_peak_strike":row.get("put_peak_strike"),
            "call_peak_distance":row.get("call_peak_distance"),
            "put_peak_distance":row.get("put_peak_distance"),
            "atm_call_iv":row.get("atm_call_iv"),
            "atm_put_iv":row.get("atm_put_iv"),
        })

        if progress_every and i%progress_every==0:
            print(f"[PROGRESS] {i/len(rows)*100:6.2f}% | snapshots {i}/{len(rows)}")

    # Distribution-only analysis. No thresholds are declared as trading rules.
    summary={
        "status":"PASS",
        "snapshots":len(rows),
        "coverage_incomplete":incomplete,
        "metrics":{
            "pcr_oi":{"count":len(pcr),"median":median(pcr) if pcr else None,
                      "min":min(pcr) if pcr else None,"max":max(pcr) if pcr else None},
            "call_delta_oi":{"count":len(call_doi),"median":median(call_doi) if call_doi else None,
                             "min":min(call_doi) if call_doi else None,"max":max(call_doi) if call_doi else None},
            "put_delta_oi":{"count":len(put_doi),"median":median(put_doi) if put_doi else None,
                            "min":min(put_doi) if put_doi else None,"max":max(put_doi) if put_doi else None},
            "call_oi":{"count":len(call_oi),"median":median(call_oi) if call_oi else None},
            "put_oi":{"count":len(put_oi),"median":median(put_oi) if put_oi else None},
        },
        "notes":[
            "This phase is descriptive and does not create trading thresholds.",
            "It does not classify PCR as bullish or bearish.",
            "It does not label OI as definite writer activity.",
            "It does not change the existing setup detector or option selector.",
            "A later phase will join these snapshots to actual NIFTY setup timestamps using only same-time evidence."
        ],
        "snapshots":len(rows),
        "snapshot_records":records
    }
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    print("Option-chain setup analysis: PASS")
    print(f"Snapshots analysed: {len(rows)}")
    print(f"Coverage-incomplete: {incomplete}")
    print(f"PCR median: {summary['metrics']['pcr_oi']['median']}")
    print(f"Call ΔOI median: {summary['metrics']['call_delta_oi']['median']}")
    print(f"Put ΔOI median: {summary['metrics']['put_delta_oi']['median']}")
    print(f"Report: {output}")
    print("Trading decision integration: NOT ENABLED")
    return summary

def main(): analyse()

if __name__=="__main__": main()
