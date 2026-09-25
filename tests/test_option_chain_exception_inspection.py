from pathlib import Path
import scripts.inspect_option_chain_exceptions as mod


def test_defaults_point_to_phase10_dataset():
    assert mod.DEFAULT_OPTIONS == "data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv"
    assert mod.DEFAULT_REPORT == "data/dhan_history/reconstructed/option_chain_history_validation_report.json"


def test_script_exists():
    assert Path("scripts/inspect_option_chain_exceptions.py").exists()
