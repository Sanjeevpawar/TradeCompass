from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


MARKET_FIELDS = (
    "open", "high", "low", "close", "iv", "volume", "oi", "spot",
    "expiry_flag", "expiry_code", "requested_strike_offset", "requested_strike",
    "identity_status",
)


def _read_paths(options_dir: Path):
    return sorted(options_dir.glob("*_call.csv")), sorted(options_dir.glob("*_put.csv"))


def _load(paths):
    rows = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows


def _duplicate_analysis(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["timestamp"], row["strike"], row.get("option_type", ""))].append(row)

    duplicate_groups = [g for g in groups.values() if len(g) > 1]
    benign = 0
    conflicts = []
    for group in duplicate_groups:
        signatures = {tuple(row.get(field) for field in MARKET_FIELDS) for row in group}
        if len(signatures) == 1:
            benign += 1
        else:
            conflicts.append(group)

    return {
        "duplicate_groups": len(duplicate_groups),
        "benign_boundary_duplicates": benign,
        "true_data_conflict_groups": len(conflicts),
        "conflict_examples": [
            [
                {
                    "timestamp": r["timestamp"],
                    "strike": r["strike"],
                    "source_from_date": r.get("source_from_date"),
                    "source_to_date": r.get("source_to_date"),
                }
                for r in group
            ]
            for group in conflicts[:10]
        ],
    }


def _strike_pairing(call_rows, put_rows):
    call = defaultdict(set)
    put = defaultdict(set)
    for r in call_rows:
        call[r["timestamp"]].add(r["strike"])
    for r in put_rows:
        put[r["timestamp"]].add(r["strike"])

    all_ts = sorted(set(call) | set(put))
    count_mismatches = []
    strike_set_mismatches = []
    for ts in all_ts:
        if len(call[ts]) != len(put[ts]):
            count_mismatches.append({"timestamp": ts, "call_count": len(call[ts]), "put_count": len(put[ts])})
        if call[ts] != put[ts]:
            strike_set_mismatches.append({
                "timestamp": ts,
                "call_only_strikes": sorted(call[ts] - put[ts], key=float),
                "put_only_strikes": sorted(put[ts] - call[ts], key=float),
                "paired_strike_count": len(call[ts] & put[ts]),
                "call_count": len(call[ts]),
                "put_count": len(put[ts]),
            })

    return count_mismatches, strike_set_mismatches


def _summary(rows):
    timestamps = Counter(r["timestamp"] for r in rows)
    strikes_by_ts = defaultdict(set)
    for r in rows:
        strikes_by_ts[r["timestamp"]].add(r["strike"])
    counts = [len(v) for v in strikes_by_ts.values()]
    return {
        "rows": len(rows),
        "unique_timestamps": len(timestamps),
        "timestamp_count_min": min(timestamps.values()) if timestamps else 0,
        "timestamp_count_max": max(timestamps.values()) if timestamps else 0,
        "timestamp_count_median": median(timestamps.values()) if timestamps else 0,
        "missing_core_fields": {k: sum(1 for r in rows if not r.get(k)) for k in ("oi", "volume", "iv", "spot", "strike")},
        "unique_strikes_per_timestamp_min": min(counts) if counts else 0,
        "unique_strikes_per_timestamp_max": max(counts) if counts else 0,
        "unique_strikes_per_timestamp_median": median(counts) if counts else 0,
        "expiry_codes": dict(Counter(r.get("expiry_code") for r in rows)),
        "identity_status": dict(Counter(r.get("identity_status") for r in rows)),
    }


def validate(
    options_dir: str = "data/dhan_history/raw/options",
    report_path: str = "data/dhan_history/reconstructed/option_chain_history_validation_report.json",
):
    root = Path(options_dir)
    calls, puts = _read_paths(root)
    call_rows = _load(calls)
    put_rows = _load(puts)

    call_duplicates = _duplicate_analysis(call_rows)
    put_duplicates = _duplicate_analysis(put_rows)
    count_mismatches, strike_set_mismatches = _strike_pairing(call_rows, put_rows)

    true_conflicts = call_duplicates["true_data_conflict_groups"] + put_duplicates["true_data_conflict_groups"]
    status = "PASS" if true_conflicts == 0 else "BLOCKED"

    report = {
        "status": status,
        "purpose": "Validate whether Dhan historical rolling-option data can support a non-look-ahead local option-chain research layer.",
        "coverage": {"call_files": len(calls), "put_files": len(puts)},
        "call": {**_summary(call_rows), "duplicate_analysis": call_duplicates},
        "put": {**_summary(put_rows), "duplicate_analysis": put_duplicates},
        "call_put_timestamp_count_mismatches": count_mismatches,
        "call_put_strike_set_mismatches": strike_set_mismatches,
        "research_interpretation": {
            "duplicate_timestamp_strike_pairs": "The observed duplicates are boundary-overlap rows when their market fields are identical; source chunk metadata may differ and is not market data.",
            "chain_pairing": "For chain metrics, Call and Put values should be paired by timestamp + strike + fixed/derived contract identity. Timestamps with incomplete strike pairing must be flagged or use only the common strike intersection.",
            "oi_change": "Calculate OI change only within the same fixed contract identity; never across expiry or rolling-boundary transitions.",
            "writer_language": "Large OI concentration is a potential positioning zone; OI alone does not prove participant side or writer identity.",
        },
        "research_limitations": [
            "Rolling historical data is relative to spot and provides up to ATM +/- 10 strikes for near-expiry index options.",
            "The historical rolling response does not directly expose the historical expiry date; contract identity remains derived.",
            "Historical chain snapshots must not use later timestamps or end-of-day values.",
        ],
        "recommended_next_step": "Build the chain snapshot engine only after excluding/flagging incomplete strike-pair timestamps and preserving fixed-contract identity boundaries.",
    }
    out = Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--options-dir", default="data/dhan_history/raw/options")
    parser.add_argument("--report", default="data/dhan_history/reconstructed/option_chain_history_validation_report.json")
    args = parser.parse_args()
    report = validate(args.options_dir, args.report)
    print(f"Option-chain historical integrity: {report['status']}")
    print(f"Call rows: {report['call']['rows']}")
    print(f"Put rows: {report['put']['rows']}")
    print(f"Unique timestamps: {report['call']['unique_timestamps']}")
    print(f"Call benign boundary duplicates: {report['call']['duplicate_analysis']['benign_boundary_duplicates']}")
    print(f"Put benign boundary duplicates: {report['put']['duplicate_analysis']['benign_boundary_duplicates']}")
    print(f"True Call data conflicts: {report['call']['duplicate_analysis']['true_data_conflict_groups']}")
    print(f"True Put data conflicts: {report['put']['duplicate_analysis']['true_data_conflict_groups']}")
    print(f"Call/put timestamp-count mismatches: {len(report['call_put_timestamp_count_mismatches'])}")
    print(f"Call/put strike-set mismatches: {len(report['call_put_strike_set_mismatches'])}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
