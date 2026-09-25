from __future__ import annotations

import csv
from pathlib import Path

from scripts.validate_historical_research_policy import validate


def _write(path: Path, rows: list[dict]) -> None:
    fields = ["timestamp", "expiry", "strike", "option_type", "open", "close", "contract_identity_status", "contract_continuity", "reconstruction_eligible"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides):
    row = {
        "timestamp": "2026-03-23T09:15:00+05:30",
        "expiry": "2026-03-24",
        "strike": "24000",
        "option_type": "CE",
        "open": "100",
        "close": "101",
        "contract_identity_status": "DERIVED",
        "contract_continuity": "CONTINUOUS",
        "reconstruction_eligible": "true",
    }
    row.update(overrides)
    return row


def test_policy_accepts_derived_identity_and_valid_dte(tmp_path):
    path = tmp_path / "options.csv"
    _write(path, [_row()])
    report = validate(path)
    assert report["status"] == "PASS"
    assert report["research_policy"]["broker_verified_expiry"] is False
    assert report["dte"]["negative_rows"] == 0


def test_policy_warns_on_holiday_expiry_without_auto_repair(tmp_path):
    path = tmp_path / "options.csv"
    _write(path, [_row(expiry="2026-03-31", timestamp="2026-03-30T09:15:00+05:30")])
    report = validate(path)
    assert report["status"] == "PASS_WITH_WARNINGS"
    assert report["holiday_expiry_rows"]["2026-03-31"] == 1
    assert report["research_policy"]["auto_repair_existing_dataset"] is False


def test_policy_strict_mode_blocks_holiday_expiry(tmp_path):
    path = tmp_path / "options.csv"
    _write(path, [_row(expiry="2026-03-31", timestamp="2026-03-30T09:15:00+05:30")])
    report = validate(path, fail_on_holiday_expiry=True)
    assert report["status"] == "BLOCKED"


def test_policy_detects_negative_dte(tmp_path):
    path = tmp_path / "options.csv"
    _write(path, [_row(expiry="2026-03-20")])
    report = validate(path)
    assert report["dte"]["negative_rows"] == 1
    assert any("Negative DTE" in warning for warning in report["warnings"])
