# TradeCompass Phase 8.4 — Dhan Sample Validation Gate

## Goal

Validate the Phase 8.3 enriched Dhan sample as a research-data layer before converting anything into the contract-aware backtester.

Dhan's rolling expired-options API provides rolling strike-relative data with OHLC, IV, volume, OI and spot, but does not return a historical expiry field in the rolling response. Dhan documents `expiryCode` 0/1/2 as current/near, next and far expiry. Therefore Phase 8.4 treats the Phase 8.3 expiry and Delta as derived fields and validates their internal consistency rather than claiming broker-confirmed contract identity.

## Validation checks

- CALL/PUT timestamps are paired.
- CALL/PUT strike, spot, derived expiry and DTE agree at each paired timestamp.
- CALL Delta is in [0,1]; PUT Delta is in [-1,0].
- CALL Delta minus PUT Delta is close to 1.
- DTE never increases as the sample moves forward.
- timestamps are strictly increasing within each series.
- the short sample has one derived expiry per side.
- option timestamps align with the underlying sample.
- ATM-like observations get a warning rather than a hard failure if model Delta is not roughly +/-0.5.

Strike changes are **not** treated as errors: Dhan's rolling ATM series is relative to spot, so a changing strike is expected.

## Run

From the TradeCompass root:

```powershell
py -m pytest -q tests/test_sample_validation.py
```

Then validate the actual enriched sample:

```powershell
py -m scripts.validate_dhan_sample
```

The command writes:

`data/dhan_samples/validation_report.json`

The command exits with code 1 if any hard validation error is found.

## Research gate

A PASS means the sample is internally consistent enough to proceed to the next investigation. It does **not** prove that Dhan's rolling observation maps to a specific exchange contract ID. Before backtesting, an independent contract source / instrument master should still be used to validate expiry and contract identity.

## Source notes

Dhan's official documentation describes the rolling endpoint as minute-level expired-options data based on strike relative to spot, and the instrument master contains explicit expiry date, strike and option type fields. NSE's current contract specifications state that NIFTY 50 index options expire Tuesday, with the previous trading day used if Tuesday is a trading holiday. The 2026 NSE holiday calendar includes 14-Sep-2026 as a Monday holiday, relevant to the week after this sample.
