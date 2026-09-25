from pathlib import Path
import csv

from scripts.validate_raw_acquisition import boundary_duplicates_detail


def write_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "strike", "option_type"])
        w.writerows(rows)


def test_expected_boundary_duplicate_is_allowed(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    write_csv(a, [("2026-01-01T09:15:00+05:30", "24000", "CE")])
    write_csv(b, [("2026-01-01T09:15:00+05:30", "24000", "CE")])
    expected, unexpected = boundary_duplicates_detail(a, b, True, "2026-01-01")
    assert expected == 1 and len(unexpected) == 0


def test_duplicate_outside_boundary_is_rejected(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    write_csv(a, [("2026-01-01T09:15:00+05:30", "24000", "CE")])
    write_csv(b, [("2026-01-01T09:15:00+05:30", "24000", "CE")])
    expected, unexpected = boundary_duplicates_detail(a, b, True, "2026-01-02")
    assert expected == 0 and len(unexpected) == 1


def test_epoch_timestamp_is_supported_in_ist(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    # 2026-01-01 09:15 IST
    write_csv(a, [("1767239100", "24000", "CE")])
    write_csv(b, [("1767239100", "24000", "CE")])
    expected, unexpected = boundary_duplicates_detail(a, b, True, "2026-01-01")
    assert expected == 1 and len(unexpected) == 0


def test_no_duplicate_is_clean(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    write_csv(a, [("2026-01-01T09:15:00+05:30", "24000", "CE")])
    write_csv(b, [("2026-01-02T09:15:00+05:30", "24000", "CE")])
    expected, unexpected = boundary_duplicates_detail(a, b, True, "2026-01-02")
    assert expected == 0 and len(unexpected) == 0
