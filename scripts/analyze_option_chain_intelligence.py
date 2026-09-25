from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, median


FIELDS_NUMERIC = [
    "pcr_oi", "call_peak_oi_pct", "put_peak_oi_pct",
    "call_peak_distance", "put_peak_distance",
    "call_delta_oi", "put_delta_oi",
    "atm_call_iv", "atm_put_iv", "atm_call_oi", "atm_put_oi",
]


def finite_values(rows, field):
    out = []
    for row in rows:
        value = row.get(field)
        if isinstance(value, (int, float)) and math.isfinite(value):
            out.append(float(value))
    return out


def stats(values):
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    n = len(ordered)
    def pct(p):
        if n == 1:
            return ordered[0]
        pos = (n - 1) * p
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        return ordered[lo] + (ordered[hi] - ordered[lo]) * frac
    return {
        "count": n,
        "min": ordered[0],
        "p05": pct(0.05),
        "p25": pct(0.25),
        "median": median(ordered),
        "p75": pct(0.75),
        "p95": pct(0.95),
        "max": ordered[-1],
        "mean": mean(ordered),
    }


def top_counts(rows, field, limit=10):
    counts = {}
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]


def analyse(rows, progress_every=1000):
    total = len(rows)
    warnings = []
    if total == 0:
        raise ValueError("No snapshots found in the report")

    coverage_incomplete = sum(1 for r in rows if not r.get("coverage_complete", False))
    derived_identity = sum(1 for r in rows if r.get("identity_status") == "DERIVED")
    unknown_identity = sum(1 for r in rows if r.get("identity_status") == "UNKNOWN" or not r.get("identity_status"))

    for i in range(0, total, progress_every):
        done = min(i + progress_every, total)
        pct = done / total * 100
        print(f"[PROGRESS] {pct:6.2f}% | snapshots {done}/{total}")

    for field in FIELDS_NUMERIC:
        values = finite_values(rows, field)
        if field == "pcr_oi":
            extreme = sum(1 for v in values if v <= 0 or v > 10)
            if extreme:
                warnings.append(f"PCR has {extreme} values <= 0 or > 10; inspect before using as a rule")
        if field.endswith("_iv"):
            invalid = sum(1 for v in values if v < 0 or v > 500)
            if invalid:
                warnings.append(f"{field} has {invalid} values outside 0..500; inspect before use")

    pcr = finite_values(rows, "pcr_oi")
    call_dist = finite_values(rows, "call_peak_distance")
    put_dist = finite_values(rows, "put_peak_distance")
    call_delta = finite_values(rows, "call_delta_oi")
    put_delta = finite_values(rows, "put_delta_oi")

    # A descriptive classification only; this is not a trading signal.
    pcr_buckets = {
        "<0.75": sum(v < 0.75 for v in pcr),
        "0.75-1.00": sum(0.75 <= v < 1.0 for v in pcr),
        "1.00-1.25": sum(1.0 <= v < 1.25 for v in pcr),
        "1.25-1.50": sum(1.25 <= v < 1.5 for v in pcr),
        ">=1.50": sum(v >= 1.5 for v in pcr),
    }

    result = {
        "status": "PASS_WITH_WARNINGS" if warnings else "PASS",
        "purpose": "Descriptive analysis of the independently built historical option-chain evidence layer. No trading rule or signal is produced.",
        "snapshot_count": total,
        "coverage_incomplete_snapshots": coverage_incomplete,
        "identity": {"DERIVED": derived_identity, "UNKNOWN": unknown_identity},
        "numeric_summary": {field: stats(finite_values(rows, field)) for field in FIELDS_NUMERIC},
        "pcr_buckets": pcr_buckets,
        "peak_distance_summary": {
            "call_peak_distance": stats(call_dist),
            "put_peak_distance": stats(put_dist),
        },
        "delta_oi_summary": {
            "call_delta_oi": stats(call_delta),
            "put_delta_oi": stats(put_delta),
            "call_positive_pct": (sum(v > 0 for v in call_delta) / len(call_delta) * 100) if call_delta else None,
            "put_positive_pct": (sum(v > 0 for v in put_delta) / len(put_delta) * 100) if put_delta else None,
        },
        "common_strike_counts": top_counts(rows, "common_strikes"),
        "warnings": warnings,
        "research_notes": [
            "This is descriptive research only; no BUY CALL, BUY PUT, WAIT, score, or option-selection decision is produced.",
            "The historical chain is near-ATM/rolling rather than a full option chain.",
            "PCR is based on common Call/Put strikes only.",
            "Large OI is concentration evidence, not proof of option writers.",
            "Expiry identity remains derived and is not repaired here.",
            "Any future chain rule must be tested against the same historical timestamps without look-ahead.",
        ],
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Descriptive analysis of historical option-chain intelligence.")
    parser.add_argument("--input", default="data/dhan_history/reconstructed/option_chain_intelligence_1y.json")
    parser.add_argument("--output", default="data/dhan_history/reconstructed/option_chain_intelligence_analysis_1y.json")
    parser.add_argument("--progress-every", type=int, default=1000)
    args = parser.parse_args()

    source = Path(args.input)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload.get("snapshots_data", [])
    result = analyse(rows, progress_every=max(1, args.progress_every))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("Option-chain intelligence analysis: " + result["status"])
    print(f"Snapshots analysed: {result['snapshot_count']}")
    print(f"Coverage-incomplete: {result['coverage_incomplete_snapshots']}")
    print(f"PCR median: {result['numeric_summary']['pcr_oi'].get('median')}")
    print(f"Call ΔOI median: {result['numeric_summary']['call_delta_oi'].get('median')}")
    print(f"Put ΔOI median: {result['numeric_summary']['put_delta_oi'].get('median')}")
    print(f"Report: {args.output}")
    print("Trading decision integration: NOT ENABLED")


if __name__ == "__main__":
    main()
