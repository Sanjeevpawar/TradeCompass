
from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import median
from typing import Any

from analysis.v2.quant_engine import analyze_market
from data.candle_models import Candle
from strategy.v2.buying_rules import evaluate_buying_setups


UNDERLYING = Path("data/dhan_history/reconstructed/nifty_underlying_1y.csv")
CHAIN = Path("data/dhan_history/reconstructed/option_chain_intelligence_1y.json")
OUTPUT = Path("data/dhan_history/reconstructed/chain_vs_setup_analysis_1y.json")


def _float(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _load_candles(path: Path) -> list[Candle]:
    out=[]
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            try:
                out.append(Candle(
                    timestamp=str(r["timestamp"]),
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=int(float(r.get("volume",0) or 0)),
                    oi=int(float(r["oi"])) if r.get("oi") not in (None,"") else None,
                ))
            except (KeyError,TypeError,ValueError):
                continue
    return out


def _load_chain(path: Path) -> dict[str,dict[str,Any]]:
    d=json.loads(path.read_text(encoding="utf-8"))
    rows=d.get("snapshots_data")
    if not isinstance(rows,list):
        raise ValueError("Expected snapshots_data list in option-chain intelligence report")
    result={}
    for r in rows:
        ts=r.get("timestamp")
        if ts:
            result[str(ts)] = r
    return result


def _chain_value(row, *keys):
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None


def _forward_metrics(candles, i, direction, horizons=(1,3,6,12)):
    entry=candles[i].close
    future=candles[i+1:i+1+max(horizons)]
    if not future or entry == 0:
        return {"future_bars":len(future),"mfe_points":None,"mae_points":None,
                "mfe_pct":None,"mae_pct":None,"forward_returns":{}}
    if direction=="CALL":
        mfe=max(c.high for c in future)-entry
        mae=min(c.low for c in future)-entry
    else:
        mfe=entry-min(c.low for c in future)
        mae=entry-max(c.high for c in future)
    returns={}
    for h in horizons:
        if len(future)>=h:
            close=future[h-1].close
            returns[str(h)] = (close-entry)/entry*100 if direction=="CALL" else (entry-close)/entry*100
    return {
        "future_bars":len(future),
        "mfe_points":round(mfe,2),
        "mae_points":round(mae,2),
        "mfe_pct":round(mfe/entry*100,4),
        "mae_pct":round(mae/entry*100,4),
        "forward_returns":returns,
    }


def analyse(underlying_path=UNDERLYING, chain_path=CHAIN, output_path=OUTPUT, progress_every=1000):
    candles=_load_candles(Path(underlying_path))
    chain=_load_chain(Path(chain_path))
    if len(candles)<35:
        raise ValueError(f"Need at least 35 underlying candles; received {len(candles)}")

    occurrences=[]
    missing_chain=0
    total_signal_events=0

    # Each analysis uses only candles through the signal candle.
    for i in range(30,len(candles)-1):
        analysis=analyze_market(candles[:i+1])
        signals=evaluate_buying_setups(analysis)
        valid=[s for s in signals if s.get("signal") in ("BUY_CALL","BUY_PUT") and s.get("score",0)>=70]
        if not valid:
            if (i+1)%progress_every==0:
                print(f"[PROGRESS] {(i+1)/len(candles)*100:6.2f}% | candles {i+1}/{len(candles)} | setups {len(occurrences)}")
            continue

        total_signal_events += len(valid)
        ts=str(candles[i].timestamp)
        chain_row=chain.get(ts)
        if chain_row is None:
            missing_chain += len(valid)

        for signal in valid:
            direction=signal["direction"]
            rec={
                "timestamp":ts,
                "direction":direction,
                "signal":signal["signal"],
                "setup":signal["setup"],
                "score":signal["score"],
                "strength":signal.get("strength"),
                "reasons":signal.get("reasons",[]),
                "warnings":signal.get("warnings",[]),
                "nifty_close":candles[i].close,
                "chain_available":chain_row is not None,
                "chain":None,
                "forward":_forward_metrics(candles,i,direction),
            }
            if chain_row is not None:
                rec["chain"]={
                    "identity_status":chain_row.get("identity_status"),
                    "coverage_complete":chain_row.get("coverage_complete"),
                    "pcr_oi":_chain_value(chain_row,"pcr_oi"),
                    "call_oi":_chain_value(chain_row,"call_oi"),
                    "put_oi":_chain_value(chain_row,"put_oi"),
                    "call_delta_oi":_chain_value(chain_row,"call_delta_oi"),
                    "put_delta_oi":_chain_value(chain_row,"put_delta_oi"),
                    "call_peak_strike":_chain_value(chain_row,"call_peak_strike","highest_call_oi_strike"),
                    "put_peak_strike":_chain_value(chain_row,"put_peak_strike","highest_put_oi_strike"),
                    "call_peak_distance":_chain_value(chain_row,"call_peak_distance"),
                    "put_peak_distance":_chain_value(chain_row,"put_peak_distance"),
                    "atm_call_iv":_chain_value(chain_row,"atm_call_iv"),
                    "atm_put_iv":_chain_value(chain_row,"atm_put_iv"),
                }
            occurrences.append(rec)

        if (i+1)%progress_every==0:
            print(f"[PROGRESS] {(i+1)/len(candles)*100:6.2f}% | candles {i+1}/{len(candles)} | setups {len(occurrences)}")

    complete=[r for r in occurrences if r["chain_available"] and r["chain"].get("coverage_complete") is not False]
    pcr=[_float(r["chain"]["pcr_oi"]) for r in complete if _float(r["chain"]["pcr_oi"]) is not None]
    call_doi=[_float(r["chain"]["call_delta_oi"]) for r in complete if _float(r["chain"]["call_delta_oi"]) is not None]
    put_doi=[_float(r["chain"]["put_delta_oi"]) for r in complete if _float(r["chain"]["put_delta_oi"]) is not None]

    summary={
        "status":"PASS",
        "candles_analysed":len(candles),
        "chain_snapshots":len(chain),
        "signal_events":total_signal_events,
        "setup_occurrences":len(occurrences),
        "chain_missing_for_setup":missing_chain,
        "complete_chain_setup_occurrences":len(complete),
        "descriptive_chain_metrics":{
            "pcr_median":median(pcr) if pcr else None,
            "call_delta_oi_median":median(call_doi) if call_doi else None,
            "put_delta_oi_median":median(put_doi) if put_doi else None,
        },
        "research_policy":{
            "same_timestamp_chain_only":True,
            "setup_uses_only_completed_candles":True,
            "forward_outcome_is_not_used_in_signal":True,
            "no_chain_thresholds_created":True,
            "no_strategy_integration":True,
            "no_option_selection":True,
            "no_live_trading":True,
        },
        "occurrences":occurrences,
    }
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    Path(output_path).write_text(json.dumps(summary,indent=2,default=str),encoding="utf-8")
    print("Chain vs setup analysis: PASS")
    print(f"Candles analysed: {len(candles)}")
    print(f"Setup occurrences: {len(occurrences)}")
    print(f"Complete-chain setup occurrences: {len(complete)}")
    print(f"Missing chain at setup: {missing_chain}")
    print(f"PCR median at setups: {summary['descriptive_chain_metrics']['pcr_median']}")
    print(f"Call ΔOI median at setups: {summary['descriptive_chain_metrics']['call_delta_oi_median']}")
    print(f"Put ΔOI median at setups: {summary['descriptive_chain_metrics']['put_delta_oi_median']}")
    print(f"Report: {output_path}")
    print("Trading decision integration: NOT ENABLED")
    return summary


def main():
    analyse()


if __name__=="__main__":
    main()
