# TradeCompass Phase 8.3 — Historical Contract Identity & Delta Reconstruction

## Goal

Convert Dhan's rolling expired-option sample into a **research-ready derived contract layer** without pretending that Dhan returned an explicit historical expiry or Greek.

Dhan's rolling expired-options endpoint returns timestamp, OHLC, IV, volume, strike, OI and spot. It does **not** return an explicit expiry-date field in this response. Dhan documents `expiryCode` as 0 = current/near, 1 = next, 2 = far. Therefore this phase derives expiry from the exchange calendar and records the derivation method/confidence instead of silently treating it as broker-confirmed identity.

## Important research rule

`derived_expiry` is **not** the same as an exchange-confirmed historical contract ID.

Likewise, `model_delta` is an approximate Black-Scholes delta calculated from Dhan's IV, spot and strike. It is not a broker-reported historical Greek. Defaults use zero rates/dividend yield because the rolling endpoint does not provide those inputs.

These fields must be validated before they are allowed into the contract-aware backtester.

## Expiry calendar logic

- NIFTY weekly contracts expiring on/after 1 Sep 2025 use Tuesday expiry.
- If Tuesday is a trading holiday, expiry moves to the previous trading day.
- For pre-1 Sep 2025 weekly research, the module retains the older Thursday regime rather than applying the modern Tuesday rule.
- On an expiry day, the current contract is considered active through the 15:30 IST cutoff; after that, the next expiry becomes the current/near contract.

For a Dhan `expiryCode=1` sample, the resolver selects the second applicable future expiry from the observation timestamp.

## Run against the captured sample

From the TradeCompass root:

```powershell
py -m scripts.enrich_dhan_sample --input data/dhan_samples/nifty_options_call.csv --output data/dhan_samples/nifty_options_call_enriched.csv
py -m scripts.enrich_dhan_sample --input data/dhan_samples/nifty_options_put.csv --output data/dhan_samples/nifty_options_put_enriched.csv
```

Expected outputs:

- `derived_expiry`
- `dte_days`
- `time_to_expiry_years`
- `model_delta`
- `delta_source`
- `identity_method`
- `identity_confidence`
- `identity_note`

## What this phase does NOT do

- It does not claim the rolling series is a specific exchange contract ID.
- It does not invent bid/ask prices.
- It does not use model delta as if it were Dhan's historical delta.
- It does not connect the enriched rows to the backtester yet.
- It does not place or simulate live orders.

## Validation gate before Phase 8.4

We need to compare derived expiry/strike continuity against an independent contract source for the sample and at least one expiry transition. Only after that should the enriched rows be converted into `HistoricalOptionBar` objects for contract-aware backtesting.
