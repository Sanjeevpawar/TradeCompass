from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .fixed_contract_reconstruction import reconstruct_fixed_contracts, write_csv, write_report

IST = ZoneInfo("Asia/Kolkata")


def _text(v):
    return "" if v is None else str(v).strip()


def parse_timestamp(value) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt.astimezone(IST)
    except ValueError:
        pass
    try:
        epoch = float(text)
        if epoch > 1_000_000_000_000:
            epoch /= 1000.0
        return datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone(IST)
    except (ValueError, OverflowError, OSError):
        return None


def next_weekly_expiry(ts: datetime) -> date:
    """Derive the next NIFTY weekly expiry for the acquired expiryCode=1 stream.

    The acquisition starts in Sep-2025, when NIFTY weekly expiry was Tuesday.
    Dhan's rolling stream rolls after the expiry session, so Tuesday 15:30+ is
    assigned to the following week's expiry. This remains DERIVED, not broker-verified.
    """
    d = ts.date()
    days_to_tuesday = (1 - d.weekday()) % 7
    if days_to_tuesday == 0 and ts.time() >= time(15, 30):
        days_to_tuesday = 7
    elif days_to_tuesday == 0:
        # Before the expiry session closes, expiryCode=1 is the following Tuesday.
        days_to_tuesday = 7
    return d + timedelta(days=days_to_tuesday)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def enrich_option_row(row: dict[str, str], source: Path, side: str) -> dict[str, str] | None:
    ts = parse_timestamp(row.get("timestamp"))
    if ts is None:
        return None
    out = dict(row)
    out["timestamp"] = ts.isoformat()
    out["derived_expiry"] = _text(row.get("expiry") or row.get("derived_expiry")) or next_weekly_expiry(ts).isoformat()
    out["option_type"] = "CE" if side.lower() == "call" else "PE"
    out["identity_status"] = _text(row.get("identity_status")) or "DERIVED"
    out["source_file"] = str(source)
    return out


def dedupe_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict]:
    by_key: dict[tuple, dict[str, str]] = {}
    duplicates = 0
    conflicts = []
    for row in rows:
        key = (row["timestamp"], row.get("strike", ""), row["option_type"])
        if key in by_key:
            duplicates += 1
            prior = by_key[key]
            comparable = ("open", "high", "low", "close", "volume", "oi", "iv", "spot")
            if any(_text(prior.get(k)) != _text(row.get(k)) for k in comparable):
                conflicts.append({"key": key, "first_source": prior.get("source_file"), "second_source": row.get("source_file")})
            continue
        by_key[key] = row
    return list(by_key.values()), {"duplicates_removed": duplicates, "conflicting_duplicates": conflicts}


def collect_raw(raw_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict]:
    options_dir = raw_root / "options"
    call_files = sorted(options_dir.glob("options_*_call.csv"))
    put_files = sorted(options_dir.glob("options_*_put.csv"))
    if not call_files or not put_files:
        raise FileNotFoundError("Expected option chunk files under data/dhan_history/raw/options")

    option_rows: list[dict[str, str]] = []
    rejected = 0
    for side, files in (("call", call_files), ("put", put_files)):
        for path in files:
            for raw in read_csv(path):
                enriched = enrich_option_row(raw, path, side)
                if enriched is None:
                    rejected += 1
                else:
                    option_rows.append(enriched)

    deduped, dedupe_report = dedupe_rows(option_rows)

    underlying_rows: list[dict[str, str]] = []
    underlying_files = sorted((raw_root / "underlying").glob("underlying_*.csv"))
    for path in underlying_files:
        for raw in read_csv(path):
            ts = parse_timestamp(raw.get("timestamp"))
            if ts is None:
                continue
            out = dict(raw)
            out["timestamp"] = ts.isoformat()
            out["source_file"] = str(path)
            underlying_rows.append(out)
    # Underlying boundary rows are intentionally duplicated by acquisition chunks.
    ub: dict[str, dict[str, str]] = {}
    u_conflicts = []
    for row in underlying_rows:
        key = row["timestamp"]
        if key in ub:
            comparable = ("open", "high", "low", "close", "volume", "oi")
            if any(_text(ub[key].get(k)) != _text(row.get(k)) for k in comparable):
                u_conflicts.append({"timestamp": key, "first_source": ub[key].get("source_file"), "second_source": row.get("source_file")})
            continue
        ub[key] = row
    return deduped, list(ub.values()), {
        "option_files": {"call": len(call_files), "put": len(put_files)},
        "underlying_files": len(underlying_files),
        "option_rows_rejected_timestamp": rejected,
        "option_dedupe": dedupe_report,
        "underlying_duplicates_removed": len(underlying_rows) - len(ub),
        "underlying_conflicting_duplicates": u_conflicts,
    }


def run_full_year(raw_root: str | Path, output_dir: str | Path) -> dict:
    raw_root = Path(raw_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    options, underlying, ingest = collect_raw(raw_root)
    fixed, report = reconstruct_fixed_contracts(options, expected_interval_minutes=5)
    report["status"] = "PASS" if not ingest["option_dedupe"]["conflicting_duplicates"] and not ingest["underlying_conflicting_duplicates"] else "FAIL"
    report["phase"] = "10.5_full_year_fixed_contract_reconstruction"
    report["identity_policy"] = "DERIVED; no broker verification inferred from current instrument master"
    report["expiry_policy"] = "Tuesday NIFTY weekly expiry derived for expiryCode=1; Tuesday 15:30+ rolls to following week"
    report["ingest"] = ingest
    report["raw_root"] = str(raw_root)
    report["outputs"] = {
        "fixed_contracts": str(output_dir / "nifty_fixed_contracts_1y.csv"),
        "underlying": str(output_dir / "nifty_underlying_1y.csv"),
        "report": str(output_dir / "full_year_reconstruction_report.json"),
    }
    write_csv(fixed, output_dir / "nifty_fixed_contracts_1y.csv")
    write_csv(underlying, output_dir / "nifty_underlying_1y.csv")
    write_report(report, output_dir / "full_year_reconstruction_report.json")
    return report
