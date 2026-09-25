# TradeCompass Phase 12 — Canonical Production Core

Phase 12 introduces the canonical read-only production decision path without removing the existing research/backtest code.

## Production path

Market candles + option chain → technical evidence + chain evidence → decision → suggested option → risk check → one TradeCompass signal.

Production decisions are only:

- `BUY_CALL`
- `BUY_PUT`
- `WAIT`

Technical and chain analysis are evidence modules, not competing production signals.

## Important safeguards

- No order placement.
- No quantity recommendation.
- No planned capital or position sizing in the production risk output.
- PCR is contextual evidence, not a standalone trigger.
- OI concentration is described as a zone, not proof of trader intent.
- OI migration compares successive chain snapshots.
- Every decision is persisted as an immutable signal snapshot.
- Signal events are append-only.
- Completed candles only are used for the official decision.

## Compatibility

The existing Phase 11 live engine remains available for regression compatibility. Phase 12 is the new canonical production path and can be wired into the dashboard after validation.
