# TradeCompass Phase 8.5 — Rolling Contract Validation

## Purpose

Phase 8.4 correctly exposed that Dhan's rolling expired-options data is not a
single fixed contract. Phase 8.5 changes validation accordingly.

Dhan's rolling endpoint is explicitly rolling and strike-relative to spot. It
returns OHLC, IV, volume, OI, strike and spot, but the rolling response does
not itself provide the explicit historical contract expiry/security ID.

This phase therefore:

1. Segments observations by derived expiry.
2. Requires DTE to be non-increasing *within* an expiry segment.
3. Allows DTE to reset when the rolling expiry changes.
4. Keeps exact timestamp matching for backtest eligibility.
5. Treats missing underlying timestamps as exclusions, not fabricated candles.
6. Treats small option-spot vs underlying-close differences as warnings.
7. Optionally cross-checks derived identity against Dhan's detailed instrument master.
8. Does NOT authorize the sample for backtesting automatically.

## Test

From the TradeCompass root:

```powershell
py -m pytest -q tests/test_rolling_contract_validation.py
```

Expected:

```text
5 passed
```

## Validate the actual sample

```powershell
py -m scripts.validate_dhan_sample_v2
```

This creates:

```text
data/dhan_samples/validation_report_v2.json
```

## Optional: download Dhan detailed instrument master

Dhan documents these instrument-master URLs:

- compact: https://images.dhan.co/api-data/api-scrip-master.csv
- detailed: https://images.dhan.co/api-data/api-scrip-master-detailed.csv

The detailed master contains expiry date, strike, option type, underlying
security ID and expiry flag.

Download it with:

```powershell
py -m scripts.download_dhan_instrument_master --detailed
```

Then rerun validation with:

```powershell
py -m scripts.validate_dhan_sample_v2 --instrument-master data/dhan_samples/dhan_instrument_master_detailed.csv
```

A missing master match is reported as UNVERIFIED; it is not silently treated
as a valid contract.

## Backtest gate

Phase 8.5 intentionally keeps:

```text
backtest_gate.allowed = false
```

until the contract identity is cross-checked or the dataset is explicitly
classified as research-only.

Do not connect this sample to the production backtester yet.
