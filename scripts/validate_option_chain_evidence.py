
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import median

DEFAULT_REPORT = Path("data/dhan_history/reconstructed/option_chain_intelligence_1y.json")
DEFAULT_OUT = Path("data/dhan_history/reconstructed/option_chain_evidence_validation_1y.json")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _pct(x, n):
    return round((x / n) * 100.0, 4) if n else 0.0


def _embedded_snapshots(data):
    # Phase 10.17 stores the actual records under snapshots_data.
    for key in ("snapshots_data", "snapshot_data", "data"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    # Also support future/fixture variants.
    value = data.get("snapshots")
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("snapshots"), list):
        return value["snapshots"]
    return None


def _snapshot_count(data, embedded):
    if embedded is not None:
        return len(embedded)
    for key in ("snapshot_count", "snapshots_analyzed", "total_snapshots", "snapshots"):
        value = data.get(key)
        if _num(value):
            return int(value)
    return 0


def analyse(report_path: Path = DEFAULT_REPORT, out_path: Path = DEFAULT_OUT, progress_every: int = 1000):
    data = json.loads(report_path.read_text(encoding="utf-8"))
    snapshots = _embedded_snapshots(data)
    total = _snapshot_count(data, snapshots)

    incomplete = []
    pcr, call_doi, put_doi = [], [], []
    call_oi, put_oi, call_dist, put_dist = [], [], [], []
    identities = Counter()
    reasons = Counter()

    if snapshots is None:
        raise ValueError(
            "No embedded snapshot records found in option-chain intelligence report. "
            "Expected 'snapshots_data'."
        )

    for i, s in enumerate(snapshots, 1):
        complete = s.get("coverage_complete")
        if complete is False:
            incomplete.append({
                "timestamp": s.get("timestamp"),
                "call_contracts": s.get("call_contracts"),
                "put_contracts": s.get("put_contracts"),
                "common_strikes": s.get("common_strikes"),
                "call_only_strikes": s.get("call_only_strikes"),
                "put_only_strikes": s.get("put_only_strikes"),
                "identity_status": s.get("identity_status"),
            })
            reasons["call_put_strike_set_mismatch"] += 1

        ident = s.get("identity_status")
        if ident is not None:
            identities[str(ident)] += 1

        for key, target in (
            ("pcr_oi", pcr),
            ("call_delta_oi", call_doi),
            ("put_delta_oi", put_doi),
            ("call_oi", call_oi),
            ("put_oi", put_oi),
            ("call_peak_distance", call_dist),
            ("put_peak_distance", put_dist),
        ):
            v = s.get(key)
            if _num(v):
                target.append(float(v))

        if progress_every and i % progress_every == 0:
            print(f"[PROGRESS] {i/total*100:6.2f}% | snapshots {i}/{total}")

    summary = {
        "status": "PASS" if total else "INVALID",
        "snapshots": total,
        "source_report_compact": False,
        "coverage_incomplete": len(incomplete),
        "coverage_incomplete_pct": _pct(len(incomplete), total),
        "incomplete_details": incomplete,
        "incomplete_details_available": True,
        "incomplete_reasons": dict(reasons),
        "identity": dict(identities),
        "distributions": {
            "pcr_oi": {
                "count": len(pcr),
                "median": median(pcr) if pcr else None,
                "min": min(pcr) if pcr else None,
                "max": max(pcr) if pcr else None,
            },
            "call_delta_oi": {
                "count": len(call_doi),
                "median": median(call_doi) if call_doi else None,
                "min": min(call_doi) if call_doi else None,
                "max": max(call_doi) if call_doi else None,
            },
            "put_delta_oi": {
                "count": len(put_doi),
                "median": median(put_doi) if put_doi else None,
                "min": min(put_doi) if put_doi else None,
                "max": max(put_doi) if put_doi else None,
            },
            "call_oi": {"count": len(call_oi), "median": median(call_oi) if call_oi else None},
            "put_oi": {"count": len(put_oi), "median": median(put_oi) if put_oi else None},
            "call_peak_distance": {"count": len(call_dist), "median": median(call_dist) if call_dist else None},
            "put_peak_distance": {"count": len(put_dist), "median": median(put_dist) if put_dist else None},
        },
        "interpretation_policy": [
            "Descriptive statistics are not trading rules.",
            "PCR is not classified as bullish/bearish by threshold in this phase.",
            "Large OI is not labeled as definite writer activity.",
            "Missing chain coverage is not forward-filled or treated as zero.",
            "This phase does not alter BUY_CALL/BUY_PUT/WAIT or option selection.",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print("Option-chain evidence validation: PASS" if total else "Option-chain evidence validation: INVALID")
    print(f"Snapshots: {total}")
    print(f"Coverage-incomplete: {len(incomplete)}")
    print(f"PCR median: {summary['distributions']['pcr_oi']['median']}")
    print(f"Call ΔOI median: {summary['distributions']['call_delta_oi']['median']}")
    print(f"Put ΔOI median: {summary['distributions']['put_delta_oi']['median']}")
    print(f"Report: {out_path}")
    print("Trading decision integration: NOT ENABLED")
    return summary


def main():
    analyse()


if __name__ == "__main__":
    main()
