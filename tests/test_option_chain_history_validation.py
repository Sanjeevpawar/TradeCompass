from pathlib import Path
from tempfile import TemporaryDirectory
import csv

import scripts.validate_option_chain_history as validator


def test_validator_defaults_to_raw_option_directory():
    assert validator.validate.__defaults__[0] == "data/dhan_history/raw/options"


def test_validator_module_exists():
    assert Path("scripts/validate_option_chain_history.py").exists()


def test_identical_boundary_rows_are_benign_duplicates():
    rows = [
        {"timestamp": "t", "strike": "100", "option_type": "CE", "open": "1", "high": "2", "low": "1", "close": "2", "iv": "10", "volume": "5", "oi": "7", "spot": "100", "expiry_flag": "WEEK", "expiry_code": "1", "requested_strike_offset": "0", "requested_strike": "ATM", "identity_status": "DERIVED", "source_from_date": "a", "source_to_date": "b"},
        {"timestamp": "t", "strike": "100", "option_type": "CE", "open": "1", "high": "2", "low": "1", "close": "2", "iv": "10", "volume": "5", "oi": "7", "spot": "100", "expiry_flag": "WEEK", "expiry_code": "1", "requested_strike_offset": "0", "requested_strike": "ATM", "identity_status": "DERIVED", "source_from_date": "b", "source_to_date": "c"},
    ]
    result = validator._duplicate_analysis(rows)
    assert result["duplicate_groups"] == 1
    assert result["benign_boundary_duplicates"] == 1
    assert result["true_data_conflict_groups"] == 0


def test_strike_pairing_detects_same_count_but_different_strikes():
    calls = [{"timestamp": "t", "strike": "100"}, {"timestamp": "t", "strike": "110"}]
    puts = [{"timestamp": "t", "strike": "100"}, {"timestamp": "t", "strike": "120"}]
    count_mismatches, strike_mismatches = validator._strike_pairing(calls, puts)
    assert count_mismatches == []
    assert len(strike_mismatches) == 1
    assert strike_mismatches[0]["call_only_strikes"] == ["110"]
    assert strike_mismatches[0]["put_only_strikes"] == ["120"]
