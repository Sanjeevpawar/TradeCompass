# TradeCompass Phase 8.2 — Dhan Historical Sample Pipeline

## Goal
Capture a small, normalized NIFTY historical sample from Dhan before wiring the data into the contract-aware backtester.

## Run
From the TradeCompass root:

```powershell
py scripts/capture_dhan_sample.py --from-date 2026-09-01 --to-date 2026-09-05
```

Output:

- `data/dhan_samples/nifty_underlying.csv`
- `data/dhan_samples/nifty_options_call.csv`
- `data/dhan_samples/nifty_options_put.csv`
- `data/dhan_samples/metadata.json`

## Important research rule
Dhan's rolling expired-options endpoint supplies strike relative to spot (ATM/ATM+n/ATM-n) plus OHLC, IV, volume, OI and spot. It does not return an explicit historical expiry date in the rolling response. This phase therefore **does not invent expiry or Delta**. The sample is a raw/normalized evidence layer.

The next phase will reconstruct contract identity and Delta only after we define and test the expiry mapping. This avoids look-ahead or contract-mixing errors in the backtest.
