from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('validator', ROOT / 'scripts' / 'validate_reconstructed_dataset.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_required_columns_present():
    assert 'contract_key' in MOD.REQUIRED_OPTION
    assert 'reconstruction_eligible' in MOD.REQUIRED_OPTION


def test_parse_timestamp():
    assert MOD.parse_ts('2025-09-01T09:15:00+05:30').hour == 9


def test_validator_paths_are_reconstruction_paths():
    assert MOD.OPTION_FILE.name == 'nifty_fixed_contracts_1y.csv'
    assert MOD.UNDERLYING_FILE.name == 'nifty_underlying_1y.csv'


def test_expected_contract_key_shape():
    expiry, strike, option_type = '2025-09-02', 24000.0, 'CE'
    assert f'{expiry}|{strike:g}|{option_type}' == '2025-09-02|24000|CE'
