from pathlib import Path
import inspect

import scripts.run_full_year_backtest as runner
from backtesting.v2.engine import run_contract_backtest
from backtesting.v2.reconstructed_runner import run_reconstructed_backtest


def test_full_year_runner_defaults_use_phase10_dataset():
    assert runner.DEFAULT_UNDERLYING == "data/dhan_history/reconstructed/nifty_underlying_1y.csv"
    assert runner.DEFAULT_OPTIONS == "data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv"
    assert runner.DEFAULT_REPORT == "data/dhan_history/reconstructed/full_year_backtest_report.json"


def test_full_year_runner_is_separate_from_phase9b_runner():
    assert Path("scripts/run_reconstructed_backtest.py").exists()
    assert Path("scripts/run_full_year_backtest.py").exists()


def test_heartbeat_format_is_elapsed_only():
    assert runner._format_elapsed(0) == "00:00"
    assert runner._format_elapsed(65) == "01:05"
    assert runner._format_elapsed(3661) == "01:01:01"


def test_backtest_engine_exposes_progress_callback_without_changing_default_call_shape():
    params = inspect.signature(run_contract_backtest).parameters
    assert "progress_callback" in params
    assert "progress_interval" in params


def test_reconstructed_runner_exposes_progress_callback():
    params = inspect.signature(run_reconstructed_backtest).parameters
    assert "progress_callback" in params
    assert "progress_interval" in params
