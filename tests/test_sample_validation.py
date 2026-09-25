from __future__ import annotations

import csv
from pathlib import Path

from data.sample_validation import validate_sample


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _row(ts: str, epoch: int, option_type: str, delta: float) -> dict:
    return {
        "timestamp_epoch": str(epoch),
        "timestamp": ts,
        "option_type": option_type,
        "strike": "24050",
        "spot": "24042.55",
        "derived_expiry": "2026-09-08",
        "dte_days": "7",
        "model_delta": str(delta),
    }


def test_valid_pair_and_alignment(tmp_path: Path):
    ts = "2026-09-01T09:15:00+05:30"
    call = tmp_path / "c.csv"
    put = tmp_path / "p.csv"
    und = tmp_path / "u.csv"
    _write(call, [_row(ts, 1788234300, "CE", 0.50)])
    _write(put, [_row(ts, 1788234300, "PE", -0.50)])
    _write(und, [{"timestamp_epoch": "1788234300", "timestamp": ts, "close": "24042.55"}])
    report = validate_sample(call, put, und)
    assert report.status == "PASS"
    assert report.paired_timestamps == 1


def test_detects_delta_parity_problem(tmp_path: Path):
    ts = "2026-09-01T09:15:00+05:30"
    call = tmp_path / "c.csv"
    put = tmp_path / "p.csv"
    und = tmp_path / "u.csv"
    _write(call, [_row(ts, 1788234300, "CE", 0.50)])
    _write(put, [_row(ts, 1788234300, "PE", -0.20)])
    _write(und, [{"timestamp_epoch": "1788234300", "timestamp": ts, "close": "24042.55"}])
    report = validate_sample(call, put, und)
    assert report.status == "FAIL"
    assert any(i.code == "DELTA_PARITY" for i in report.issues)


def test_detects_unpaired_timestamp(tmp_path: Path):
    ts1 = "2026-09-01T09:15:00+05:30"
    ts2 = "2026-09-01T09:20:00+05:30"
    call = tmp_path / "c.csv"
    put = tmp_path / "p.csv"
    und = tmp_path / "u.csv"
    _write(call, [_row(ts1, 1788234300, "CE", 0.50), _row(ts2, 1788234600, "CE", 0.50)])
    _write(put, [_row(ts1, 1788234300, "PE", -0.50)])
    _write(und, [
        {"timestamp_epoch": "1788234300", "timestamp": ts1, "close": "24042.55"},
        {"timestamp_epoch": "1788234600", "timestamp": ts2, "close": "24039.4"},
    ])
    report = validate_sample(call, put, und)
    assert report.status == "FAIL"
    assert any("TIMESTAMP_UNPAIRED" in i.code for i in report.issues)
