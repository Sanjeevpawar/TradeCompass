# TradeCompass Phase 9B — Historical Backtest Adapter

Phase 9B connects the Phase 9A fixed-contract reconstruction output to the existing v2 contract-aware backtester.

## What it changes

1. Loads only Phase 9A `CONTINUOUS` + `reconstruction_eligible` contract rows by default.
2. Maps Phase 8/9 fields such as `model_delta` and `option_open`/`open` into `HistoricalOptionBar`.
3. Requires a full future option-bar horizon for the configured holding window by default. A trade is skipped rather than truncated when the fixed contract ends too early.
4. Keeps entry at the historical option **OPEN**.
5. Removes a subtle lookahead in option selection: premium limits are checked against the entry OPEN rather than the same candle CLOSE.
6. Makes missing bid/ask explicit. By default spread data is required. For Dhan expired-options research, `--allow-missing-spread-data` can be used as an explicit research-only mode; no spread is fabricated.
7. Preserves derived contract identity/Delta as research fields.

## Run tests

```powershell
py -m pytest -q tests/test_phase9b_adapter.py tests/test_phase9b_horizon.py
```

## Run the research backtest

After Phase 9A has produced `data/dhan_samples/nifty_fixed_contracts.csv`:

```powershell
py -m scripts.run_reconstructed_backtest --allow-missing-spread-data
```

The command writes:

`data/dhan_samples/phase9b_backtest_report.json`

## Important Dhan data limitation

Dhan's historical expired-options rolling data does not necessarily provide historical bid/ask. The Phase 9B adapter never invents a spread. If spread is unavailable, normal mode rejects the candidate. The explicit `--allow-missing-spread-data` mode is for research/integration testing only and must not be interpreted as a realistic transaction-cost/spread model.

## Gate

Phase 9B remains **research-only**. It does not place orders and does not approve the strategy for real-money use. Profitability conclusions require a materially larger historical dataset, independent data-quality validation, out-of-sample testing, walk-forward analysis, and robustness checks.
