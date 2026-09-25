# TradeCompass Phase 10.9 — Shared Live/Historical Risk Logic

## Purpose
Unify the deterministic stop, target, and position-sizing calculation used by the live risk engine and the historical contract backtester.

## Changes
- Added `risk.v2.risk_engine.calculate_trade_risk()` as the shared calculation.
- Historical backtesting now uses the same underlying invalidation logic as live risk: nearest meaningful support/VWAP for CALLs and resistance/VWAP for PUTs, with ATR fallback.
- Historical premium stop now uses the same 5%-of-premium floor and premium-risk conversion as live risk.
- Target uses the configurable minimum R multiple (`min_rr`, default 1.5) rather than a separate hard-coded backtest value.
- Position sizing uses the same risk-budget calculation.
- Added regression tests proving live risk decisions and the shared calculation agree, including VWAP invalidation.

## Files to replace
- `risk/v2/risk_engine.py`
- `backtesting/v2/engine.py`
- `tests/test_risk_engine.py`

## Validation
Full regression suite on the patched project: **78 passed**.

Do not run the 1-year backtest until the patch is merged and the user's local test suite passes.
