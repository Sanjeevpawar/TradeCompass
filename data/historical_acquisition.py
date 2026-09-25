from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from data.dhan_historical import DhanHistoricalClient, DhanHistoricalConfig, month_chunks
from data.dhan_strike_band import StrikeBandConfig, collect_strike_band, write_csv, write_report


@dataclass(frozen=True)
class AcquisitionConfig:
    security_id: str = "13"
    start_date: str = ""
    end_date: str = ""
    interval: int = 5
    expiry_flag: str = "WEEK"
    expiry_codes: tuple[int, ...] = (1,)
    offsets: tuple[int, ...] = tuple(range(-10, 11))
    output_root: str = "data/dhan_history/raw"
    pause_seconds: float = 0.5
    max_retries: int = 5
    retry_backoff_seconds: float = 1.0

    def validate(self) -> None:
        start = date.fromisoformat(self.start_date)
        end = date.fromisoformat(self.end_date)
        if end <= start:
            raise ValueError("end_date must be after start_date")
        if self.interval not in {1, 5, 15, 25, 60}:
            raise ValueError("interval must be one of 1, 5, 15, 25, 60")
        if self.expiry_flag not in {"WEEK", "MONTH"}:
            raise ValueError("expiry_flag must be WEEK or MONTH")
        if not self.expiry_codes or any(c not in {0, 1, 2} for c in self.expiry_codes):
            raise ValueError("expiry_codes must contain only 0, 1 or 2")
        if not self.offsets or any(o < -10 or o > 10 for o in self.offsets):
            raise ValueError("offsets must be within -10..10")


def ninety_day_chunks(start: str, end: str) -> list[tuple[str, str]]:
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    if end_d <= start_d:
        raise ValueError("end must be after start")
    chunks: list[tuple[str, str]] = []
    cursor = start_d
    while cursor < end_d:
        chunk_end = min(cursor + timedelta(days=90), end_d)
        chunks.append((cursor.isoformat(), chunk_end.isoformat()))
        cursor = chunk_end
    return chunks


def _chunk_id(prefix: str, start: str, end: str) -> str:
    return f"{prefix}_{start}_{end}"


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "chunks": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _underlying_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    data = response.get("data", response)
    if not isinstance(data, dict):
        return []
    timestamps = data.get("timestamp", data.get("start_Time", [])) or []
    rows: list[dict[str, Any]] = []
    fields = ("open", "high", "low", "close", "volume", "oi")
    for i, ts in enumerate(timestamps):
        row = {"timestamp": int(ts)}
        for field in fields:
            values = data.get(field) or []
            row[field] = values[i] if i < len(values) else None
        rows.append(row)
    return rows


def _underlying_chunk(client: DhanHistoricalClient, config: AcquisitionConfig, start: str, end: str) -> list[dict[str, Any]]:
    response = client.intraday_candles(
        security_id=config.security_id,
        exchange_segment="IDX_I",
        instrument="INDEX",
        interval=config.interval,
        from_date=f"{start} 09:15:00",
        to_date=f"{end} 15:30:00",
        oi=False,
    )
    return _underlying_rows(response)


def acquire_history(
    client: DhanHistoricalClient,
    config: AcquisitionConfig,
    *,
    sleep_fn: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Resumable raw historical acquisition; never transforms rolling data into fixed contracts."""
    config.validate()
    root = Path(config.output_root)
    manifest_path = root / "acquisition_manifest.json"
    manifest = _load_manifest(manifest_path)
    manifest.update({
        "version": 1,
        "security_id": config.security_id,
        "start_date": config.start_date,
        "end_date": config.end_date,
        "interval_minutes": config.interval,
        "expiry_flag": config.expiry_flag,
        "expiry_codes": list(config.expiry_codes),
        "strike_offsets": list(config.offsets),
        "policy": {
            "raw_only": True,
            "fixed_contract_identity": "not inferred by acquisition",
            "missing_prices": "never forward-fill",
            "resume": "completed PASS chunks are skipped only when output files exist",
        },
    })
    manifest.setdefault("chunks", {})

    underlying_chunks = ninety_day_chunks(config.start_date, config.end_date)
    option_chunks = month_chunks(config.start_date, config.end_date, max_days=30)
    errors: list[dict[str, Any]] = []

    for start, end in underlying_chunks:
        cid = _chunk_id("underlying", start, end)
        out = root / "underlying" / f"{cid}.csv"
        entry = manifest["chunks"].get(cid, {})
        if entry.get("status") == "PASS" and out.exists():
            continue
        try:
            rows = _underlying_chunk(client, config, start, end)
            write_csv(rows, out)
            manifest["chunks"][cid] = {"type": "underlying", "from_date": start, "to_date": end, "status": "PASS", "rows": len(rows), "output": str(out)}
        except Exception as exc:
            manifest["chunks"][cid] = {"type": "underlying", "from_date": start, "to_date": end, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
            errors.append(manifest["chunks"][cid])
        _save_manifest(manifest_path, manifest)
        if errors:
            break

    if not errors:
        band_cfg = StrikeBandConfig(
            security_id=config.security_id,
            expiry_flag=config.expiry_flag,
            expiry_codes=config.expiry_codes,
            interval=config.interval,
            offsets=config.offsets,
            pause_seconds=config.pause_seconds,
            max_retries=config.max_retries,
            retry_backoff_seconds=config.retry_backoff_seconds,
        )
        for start, end in option_chunks:
            cid = _chunk_id("options", start, end)
            call_out = root / "options" / f"{cid}_call.csv"
            put_out = root / "options" / f"{cid}_put.csv"
            report_out = root / "options" / f"{cid}_report.json"
            entry = manifest["chunks"].get(cid, {})
            if entry.get("status") == "PASS" and call_out.exists() and put_out.exists() and report_out.exists():
                continue
            try:
                rows, report = collect_strike_band(client, start_date=start, end_date=end, config=band_cfg)
                write_csv((r for r in rows if r["option_type"] == "CE"), call_out)
                write_csv((r for r in rows if r["option_type"] == "PE"), put_out)
                write_report(report, report_out)
                if report.get("status") != "PASS":
                    raise RuntimeError(f"Dhan option collection failed: {report.get('requests', {}).get('error_details', [])}")
                manifest["chunks"][cid] = {"type": "options", "from_date": start, "to_date": end, "status": "PASS", "rows": len(rows), "call_output": str(call_out), "put_output": str(put_out), "report": str(report_out)}
            except Exception as exc:
                manifest["chunks"][cid] = {"type": "options", "from_date": start, "to_date": end, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
                errors.append(manifest["chunks"][cid])
            _save_manifest(manifest_path, manifest)
            if errors:
                break

    statuses = list(manifest["chunks"].values())
    passed = sum(1 for x in statuses if x.get("status") == "PASS")
    failed = sum(1 for x in statuses if x.get("status") == "FAIL")
    result = {
        "status": "PASS" if not errors else "FAIL",
        "chunks": {"total": len(statuses), "passed": passed, "failed": failed},
        "underlying_chunks_expected": len(underlying_chunks),
        "option_chunks_expected": len(option_chunks),
        "manifest": str(manifest_path),
        "errors": errors,
    }
    manifest["last_run"] = result
    _save_manifest(manifest_path, manifest)
    return result
