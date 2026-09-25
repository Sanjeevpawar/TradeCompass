# TradeCompass Phase 8.6 — Historical Contract Dataset Builder

## Purpose

Phase 8.6 turns the validated Dhan rolling-option sample into one clean,
backtester-oriented research dataset.

It combines:

- NIFTY underlying OHLCV
- CALL and PUT option OHLC
- strike
- derived expiry
- DTE and time-to-expiry
- Dhan IV, volume, OI and spot
- model-derived Delta
- contract identity method/confidence
- exact timestamp alignment
- explicit eligibility and exclusion reasons

## Important policy

This phase **does not unlock the historical backtester**.

Dhan's rolling historical endpoint does not provide an explicit historical
contract expiry/security ID in the rolling response. Therefore the dataset
retains the derived identity and labels it `DERIVED` rather than pretending it
is broker-verified.

Missing underlying timestamps are excluded. Missing values required for option
selection are excluded. No future value is filled backward or forward.

## Inputs

```text
data/dhan_samples/nifty_underlying.csv
data/dhan_samples/nifty_options_call_enriched.csv
data/dhan_samples/nifty_options_put_enriched.csv
```

## Run

From the TradeCompass root:

```powershell
py -m scripts.build_historical_dataset
```

Expected outputs:

```text
data/dhan_samples/nifty_historical_research_dataset.csv
data/dhan_samples/historical_dataset_report.json
```

You can override paths:

```powershell
py -m scripts.build_historical_dataset --call <call.csv> --put <put.csv> --underlying <underlying.csv> --output <dataset.csv> --report <report.json>
```

## Test

```powershell
py -m pytest -q tests/test_historical_dataset_builder.py
```

Expected:

```text
4 passed
```

## Dataset rule

A row is eligible only when:

1. an exact underlying timestamp exists;
2. option OHLC, strike and spot are valid;
3. derived expiry and DTE exist and DTE is non-negative;
4. model Delta exists;
5. contract identity is not `UNVERIFIED`.

The overall backtest gate remains blocked until the next validation decision is
made deliberately.
