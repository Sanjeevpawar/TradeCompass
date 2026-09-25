from __future__ import annotations

from pathlib import Path
from dataclasses import replace
from typing import Callable

from backtesting.v2.engine import ContractBacktestConfig, run_contract_backtest
from backtesting.v2.historical_adapter import load_reconstructed_option_bars
from backtesting.v2.data_loader import load_underlying_csv


def run_reconstructed_backtest(
    underlying_path: str | Path,
    fixed_contract_path: str | Path,
    config: ContractBacktestConfig | None = None,
    *,
    allow_missing_spread_data: bool = False,
    progress_callback: Callable[[dict], None] | None = None,
    progress_interval: int = 100,
) -> dict:
    """Run the v2 engine only on Phase 9A continuous fixed-contract rows.

    This is explicitly research-only. Dhan expired-options data can lack bid/ask,
    so allowing missing spread data is opt-in and is recorded in the result.
    """
    candles = load_underlying_csv(underlying_path)
    option_bars, adapter_report = load_reconstructed_option_bars(fixed_contract_path)
    cfg = config or ContractBacktestConfig(
        require_spread_data=not allow_missing_spread_data,
        require_full_horizon=True,
    )
    if allow_missing_spread_data and cfg.require_spread_data:
        cfg = replace(cfg, require_spread_data=False)

    result = run_contract_backtest(
        candles,
        option_bars,
        cfg,
        progress_callback=progress_callback,
        progress_interval=progress_interval,
    )
    result["adapter_report"] = adapter_report
    result["research_gate"] = {
        "status": "RESEARCH_ONLY",
        "fixed_contract_input": True,
        "continuous_contract_filter": True,
        "full_horizon_required": cfg.require_full_horizon,
        "spread_data_required": cfg.require_spread_data,
        "missing_spread_allowed": allow_missing_spread_data,
        "production_live_trading": False,
    }
    return result
