# TradeCompass Phase 10 — Scalable Dhan Historical Acquisition

Phase 10 adds a **resumable raw-data acquisition layer** for building a materially larger NIFTY research dataset from Dhan.

## What it does

- Underlying NIFTY 5-minute candles are collected in **<=90-day** chunks.
- Dhan rolling expired-options data is collected in **<=30-day** chunks.
- Options use the ATM-relative band (default ATM-10 through ATM+10), preserving the **actual returned strike**.
- Expiry code, requested offset, source date range and identity status are retained as provenance.
- No fixed expiry is invented by the collector.
- No option price is forward-filled.
- Each chunk is written independently.
- A manifest allows interrupted downloads to resume without repeating completed chunks.
- Failed chunks make the acquisition fail; partial data is never silently treated as complete.

Dhan documents up to five years of minute-level expired-options rolling data, with a maximum 30-day request window. Dhan's general intraday historical API allows up to 90 days per request. See the official Dhan documentation before expanding the collection horizon.

## First run — recommended

Start with one year before attempting the full five-year collection:

```powershell
py -m scripts.acquire_dhan_history --from-date 2025-09-01 --to-date 2026-09-01
```

The default request is 5-minute data, WEEK, expiry code 1, and ATM-10..ATM+10.

## Full five-year collection

After validating the one-year acquisition and reconstruction:

```powershell
py -m scripts.acquire_dhan_history --from-date 2021-09-17 --to-date 2026-09-17
```

This is intentionally **not** the first command to run. It can make thousands of historical option requests and take substantial time.

## Resume

Run the same command again after an interruption. Completed chunks with their expected output files are skipped.

## Output

```text
data/dhan_history/raw/
  acquisition_manifest.json
  underlying/
    underlying_<from>_<to>.csv
  options/
    options_<from>_<to>_call.csv
    options_<from>_<to>_put.csv
    options_<from>_<to>_report.json
```

## Important gate

This phase **does not** reconstruct fixed contracts and **does not** run a profitability backtest. The raw rolling data must go through the existing Phase 9A reconstruction and validation pipeline first.

The trading gate remains research-only; no live orders are enabled.
