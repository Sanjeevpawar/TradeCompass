# TradeCompass Phase 10.8 — Pre-Entry Historical Option Selection

## Purpose

Fix a historical backtest look-ahead issue in option contract selection.

Previously, the selector used the simulated entry bar's OHLC-derived fields
(delta, volume, spread, and premium/open) to choose the contract that was then
entered at that same bar's OPEN. Fields such as volume and delta from a full
5-minute bar are not known at its OPEN.

## Change

The selector now requires two timestamps:

- `selection_timestamp`: the completed bar available before entry; used for
  contract-selection evidence (delta, volume, spread, IV/Greeks and the
  premium constraint via completed-bar CLOSE).
- `timestamp`: the simulated entry bar; only its OPEN is used as the simulated
  execution price.

The backtester passes the immediately preceding underlying/option timestamp as
`selection_timestamp` and the next underlying candle timestamp as the entry
`timestamp`.

## Important

This patch does **not** change the entry strategy, stop, target, position
sizing, or indicator calculations. It only removes the identified
pre-entry-information leak from historical option selection.

## Validation

- Targeted tests: 8 passed
- Full regression suite: 76 passed
