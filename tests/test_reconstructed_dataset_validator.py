from pathlib import Path
import csv
import importlib.util

import pytest


ROOT = Path(__file__).resolve().parents[1]

SPEC = importlib.util.spec_from_file_location(
    "validator",
    ROOT / "scripts" / "validate_reconstructed_dataset.py",
)

MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_required_columns_present():
    assert "contract_key" in MOD.REQUIRED_OPTION
    assert "reconstruction_eligible" in MOD.REQUIRED_OPTION


def test_parse_timestamp():
    assert MOD.parse_ts("2025-09-01T09:15:00+05:30").hour == 9


def test_validator_paths_are_reconstruction_paths():
    assert MOD.OPTION_FILE.name == "nifty_fixed_contracts_1y.csv"
    assert MOD.UNDERLYING_FILE.name == "nifty_underlying_1y.csv"


def test_expected_contract_key_shape():
    expiry, strike, option_type = "2025-09-02", 24000.0, "CE"
    assert f"{expiry}|{strike:g}|{option_type}" == "2025-09-02|24000|CE"


def make_valid_option_row(**overrides):
    row = {
        "timestamp": "2025-09-01T09:20:00+05:30",
        "option_type": "CE",
        "open": "100",
        "high": "105",
        "low": "95",
        "close": "102",
        "strike": "24000",
        "spot": "24500",
        "expiry": "2025-09-02",
        "contract_key": "2025-09-02|24000|CE",
        "contract_continuity": "CONTINUOUS",
        "contract_identity_status": "DERIVED",
        "same_day_gap_count": "0",
        "duplicate_timestamp_count": "0",
        "reconstruction_eligible": "true",
    }

    row.update(overrides)
    return row


def make_valid_underlying_row(**overrides):
    row = {
        "timestamp": "2025-09-01T09:20:00+05:30",
        "open": "24500",
        "high": "24510",
        "low": "24490",
        "close": "24505",
        "volume": "0",
        "oi": "",
        "source_file": "test.csv",
    }

    row.update(overrides)
    return row


def assert_option_row_rejected(**overrides):
    row = make_valid_option_row(**overrides)

    errors = MOD.validate_option_row(row, 1)

    assert errors, (
        f"Expected invalid option row to be rejected: "
        f"{overrides}"
    )


def assert_underlying_row_rejected(**overrides):
    row = make_valid_underlying_row(**overrides)

    errors = MOD.validate_underlying_row(row, 1)

    assert errors, (
        f"Expected invalid underlying row to be rejected: "
        f"{overrides}"
    )


def test_valid_option_row_passes():
    row = make_valid_option_row()

    errors = MOD.validate_option_row(row, 1)

    assert errors == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("option_type", "XX"),
        ("strike", "0"),
        ("strike", "-100"),
        ("spot", "0"),
        ("spot", "-1"),
        ("high", "90"),
        ("open", "110"),
        ("close", "110"),
        ("expiry", "not-a-date"),
    ],
)
def test_corrupted_option_rows_are_rejected(field, value):
    assert_option_row_rejected(**{field: value})


def test_option_invalid_ohlc_text_is_rejected():
    assert_option_row_rejected(open="invalid")


def test_option_invalid_strike_text_is_rejected():
    assert_option_row_rejected(strike="invalid")


def test_option_invalid_spot_text_is_rejected():
    assert_option_row_rejected(spot="invalid")


def test_valid_underlying_row_passes():
    row = make_valid_underlying_row()

    errors = MOD.validate_underlying_row(row, 1)

    assert errors == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("high", "24480"),
        ("open", "24520"),
        ("close", "24520"),
        ("volume", "-1"),
        ("oi", "-1"),
        ("oi", "invalid"),
        ("source_file", ""),
    ],
)
def test_corrupted_underlying_rows_are_rejected(field, value):
    assert_underlying_row_rejected(**{field: value})


def test_underlying_invalid_ohlc_text_is_rejected():
    assert_underlying_row_rejected(open="invalid")


def test_underlying_invalid_volume_text_is_rejected():
    assert_underlying_row_rejected(volume="invalid")


def test_underlying_invalid_timestamp_is_rejected():
    assert_underlying_row_rejected(
        timestamp="not-a-timestamp"
    )


def test_blank_underlying_oi_is_allowed():
    row = make_valid_underlying_row(oi="")

    errors = MOD.validate_underlying_row(row, 1)

    assert errors == []


def write_csv(path, fieldnames, rows):
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def run_validator_with_temp_files(
    tmp_path,
    monkeypatch,
    option_rows,
    underlying_rows,
):
    option_file = (
        tmp_path / "nifty_fixed_contracts_1y.csv"
    )

    underlying_file = (
        tmp_path / "nifty_underlying_1y.csv"
    )

    # The production validator calls:
    # REPORT_FILE.relative_to(ROOT)
    #
    # Therefore the temporary report must remain inside
    # the project ROOT. The input CSV files can still live
    # safely inside pytest's temporary directory.
    report_file = (
        ROOT / "tests" / "_tmp_validation_report.json"
    )

    option_fields = list(
        make_valid_option_row().keys()
    )

    underlying_fields = list(
        make_valid_underlying_row().keys()
    )

    write_csv(
        option_file,
        option_fields,
        option_rows,
    )

    write_csv(
        underlying_file,
        underlying_fields,
        underlying_rows,
    )

    monkeypatch.setattr(
        MOD,
        "OPTION_FILE",
        option_file,
    )

    monkeypatch.setattr(
        MOD,
        "UNDERLYING_FILE",
        underlying_file,
    )

    monkeypatch.setattr(
        MOD,
        "REPORT_FILE",
        report_file,
    )

    try:
        return MOD.validate()
    finally:
        if report_file.exists():
            report_file.unlink()


def test_full_validator_accepts_valid_minimal_dataset(
    tmp_path,
    monkeypatch,
):
    option_row = make_valid_option_row()

    underlying_row = make_valid_underlying_row()

    result = run_validator_with_temp_files(
        tmp_path,
        monkeypatch,
        [option_row],
        [underlying_row],
    )

    assert result == 0


def test_full_validator_rejects_duplicate_contract_timestamp(
    tmp_path,
    monkeypatch,
):
    first = make_valid_option_row()

    second = make_valid_option_row()

    result = run_validator_with_temp_files(
        tmp_path,
        monkeypatch,
        [first, second],
        [make_valid_underlying_row()],
    )

    assert result == 1


def test_full_validator_allows_different_contracts_at_same_timestamp(
    tmp_path,
    monkeypatch,
):
    call_row = make_valid_option_row(
        option_type="CE",
        contract_key="2025-09-02|24000|CE",
    )

    put_row = make_valid_option_row(
        option_type="PE",
        contract_key="2025-09-02|24000|PE",
    )

    result = run_validator_with_temp_files(
        tmp_path,
        monkeypatch,
        [call_row, put_row],
        [make_valid_underlying_row()],
    )

    assert result == 0


def test_full_validator_rejects_invalid_option_ohlc(
    tmp_path,
    monkeypatch,
):
    row = make_valid_option_row(
        high="90",
    )

    result = run_validator_with_temp_files(
        tmp_path,
        monkeypatch,
        [row],
        [make_valid_underlying_row()],
    )

    assert result == 1


def test_full_validator_rejects_invalid_underlying_ohlc(
    tmp_path,
    monkeypatch,
):
    row = make_valid_underlying_row(
        high="24480",
    )

    result = run_validator_with_temp_files(
        tmp_path,
        monkeypatch,
        [make_valid_option_row()],
        [row],
    )

    assert result == 1