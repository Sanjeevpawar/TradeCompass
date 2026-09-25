# TradeCompass Phase 10.7 — Historical Backtest Data Integration

This phase connects the validated Phase 10.5 full-year reconstructed dataset to the existing v2 historical backtest data adapter **without executing the strategy**.

## Run tests

```powershell
py -m pytest -q tests/test_historical_backtest_integration.py
```

## Run the actual integration check

```powershell
py -m scripts.validate_historical_backtest_integration
```

Expected input files:

- `data/dhan_history/reconstructed/nifty_underlying_1y.csv`
- `data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv`

The check verifies that:

- the full-year underlying file loads;
- the fixed-contract option file loads through the existing historical adapter;
- only `reconstruction_eligible=True` / `CONTINUOUS` rows reach the adapter;
- eligible row counts match;
- underlying and option timestamps overlap;
- DERIVED contract identity remains explicitly DERIVED;
- no strategy or trade execution occurs.

## Gate

This phase remains integration-only. It does not claim profitability and does not place live orders. The next phase can run the first clean baseline backtest only after this integration check passes.
