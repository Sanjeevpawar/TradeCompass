# TradeCompass Phase 10.5 — Full-Year Fixed-Contract Reconstruction

This phase converts the validated one-year Dhan rolling ATM±10 option chunks into fixed research series.

## Inputs
- `data/dhan_history/raw/options/options_*_call.csv`
- `data/dhan_history/raw/options/options_*_put.csv`
- `data/dhan_history/raw/underlying/underlying_*.csv`

## Rules
- Parse Dhan Unix-epoch timestamps and normalize to Asia/Kolkata.
- Remove only exact boundary duplicates across acquisition chunks.
- Conflicting duplicate observations fail the phase.
- Fixed contract key is `expiry + strike + CE/PE`.
- Never switch strike within a contract series.
- Never forward-fill missing option prices.
- Overnight/weekend gaps are not classified as intraday gaps.
- Expiry identity remains **DERIVED**, not broker-verified.
- For the Sep-2025 onward acquisition window, expiryCode=1 is mapped to the next Tuesday weekly expiry; the Tuesday 15:30 roll is handled explicitly.
- This phase does not approve profitability, live trading, or production deployment.

## Run

```powershell
py -m pytest -q tests/test_full_year_reconstruction.py
py -m scripts.reconstruct_full_year
```

Outputs:
- `data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv`
- `data/dhan_history/reconstructed/nifty_underlying_1y.csv`
- `data/dhan_history/reconstructed/full_year_reconstruction_report.json`
