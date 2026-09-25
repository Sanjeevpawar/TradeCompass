# TradeCompass Phase 9C — Historical Strike-Band Collector

Phase 9C collects a wider ATM-relative strike band from Dhan's rolling expired-options endpoint so fixed historical contracts can be reconstructed from more than the single rolling ATM series.

## Why this phase exists

The Phase 8 sample used only `ATM`. As NIFTY moved, Dhan returned different actual strikes. That produced many short/gapped fixed-contract fragments. Phase 9C requests `ATM-10` through `ATM+10` for index options and preserves the actual returned strike at every timestamp.

Dhan documents that the rolling expired-options endpoint supports historical data on a rolling basis, with `ATM` through `ATM±10` for index options near expiry, and up to 30 days per request.

## Safety/data policy

- The collector does **not** invent expiry dates.
- `expiry_code` and `expiry_flag` are retained as provenance.
- The returned `strike` from Dhan is preserved exactly.
- Requested ATM offset is provenance only; it is not contract identity.
- Missing prices are never forward-filled.
- Derived identity remains explicitly labelled.
- This phase does not run or unlock the backtester.

## First validation run

From the TradeCompass project root:

```powershell
py -m scripts.collect_dhan_strike_band --from-date 2026-09-01 --to-date 2026-09-05
```

This defaults to:
- NIFTY security ID `13`
- 5-minute bars
- weekly expiry
- expiry code `1`
- ATM-10 through ATM+10
- CALL + PUT

Outputs:

```text
data/dhan_samples/nifty_options_band_call.csv
data/dhan_samples/nifty_options_band_put.csv
data/dhan_samples/strike_band_collection_report.json
```

For a broader expiry-code capture, explicitly use `--expiry-codes 0,1`. Do not assume both codes are interchangeable; they represent different relative expiry selections.

After capture, the existing Phase 8.3 enrichment can derive research expiry/DTE/Delta, and Phase 9A can reconstruct fixed contracts from the enriched files.
