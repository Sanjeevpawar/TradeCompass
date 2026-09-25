# TradeCompass Phase 9A — Fixed Contract Reconstruction

## Why this phase exists

Dhan's expired-options API is **rolling by moneyness**. It can return ATM and, for index options near expiry, ATM±10 strikes. The returned `strike` is the actual strike observed at each timestamp, but the request is not a single fixed contract series.

TradeCompass cannot safely feed an ATM-rolling series directly into a positional option backtest. If the selected strike changes with spot, a backtest could accidentally continue a trade on a different contract.

Phase 9A therefore reconstructs **fixed contract series** using:

```text
SAME expiry + SAME strike + SAME option type
```

It never switches the strike inside a contract series and never forward-fills option prices.

## Inputs

The script accepts Phase 8/8.6 enriched or research CSVs containing at least:

- `timestamp`
- `strike`
- `option_type` (CE/PE or CALL/PUT)
- `expiry` or `derived_expiry`
- `open`, `high`, `low`, `close`

`identity_status` is retained when present. If absent, the reconstruction labels identity as `DERIVED` rather than claiming broker verification.

## Run against the Phase 8.6 sample

```powershell
py -m scripts.reconstruct_fixed_contracts --input data/dhan_samples/nifty_options_call_enriched.csv --input data/dhan_samples/nifty_options_put_enriched.csv
```

The default output is:

```text
data/dhan_samples/nifty_fixed_contracts.csv
data/dhan_samples/fixed_contract_reconstruction_report.json
```

## Important interpretation

The September sample was captured using `strike=ATM`. That is useful for validating the pipeline, but it is **not expected to produce long continuous fixed-contract histories** when NIFTY moves away from a strike.

For a real historical backtest dataset, the capture step should request a sufficiently wide ATM± strike band and then reconstruct each fixed strike from the returned actual `strike` field. Dhan documents ATM±10 for index options near expiry and a maximum 30-day request window. citeturn0search0

## Continuity rules

A contract is classified as:

- `CONTINUOUS`: no same-day intraday gap larger than the configured candle interval.
- `GAPPED`: at least one same-day intraday gap exists.
- `SINGLETON`: only one observation exists.
- `DUPLICATE_TIMESTAMP`: duplicate timestamp exists for the same contract key.

Overnight/weekend gaps are not treated as missing intraday bars.

## Safety gate

Phase 9A does **not** enable the production historical backtester.

It only creates and validates fixed-contract series. Contract identity remains explicitly labelled as derived unless a stronger source verifies it. The next phase can then adapt the existing backtester to consume these fixed-contract series.
