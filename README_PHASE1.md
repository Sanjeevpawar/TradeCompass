# TradeCompass — Phase 1 Stabilization

This phase deliberately keeps the existing architecture intact while making paper trading reliable enough to validate the next strategy engine.

## What was fixed

- Paper entry is now automatically recorded in the paper ledger.
- Paper trades receive stable trade IDs.
- The ledger stores a frozen decision snapshot and entry snapshot.
- Every monitor cycle can append a PnL + market snapshot.
- A paper exit is automatically recorded when monitoring exits the position.
- PnL accepts the broker's `INSTRUMENT_STRIKE` keys as well as legacy strike-only keys.
- Missing option prices are skipped instead of being interpreted as zero PnL.
- Monitoring no longer immediately exits solely because mock data produces `max_profit <= 0`.
- Added regression tests for the paper-trading path.

## Deliberately NOT built yet

1. Live Dhan market data
2. Option-buying strategy engine
3. Historical backtester
4. AI reasoning layer
5. Production database
6. Live order execution

Those are the next layers. The existing option-selling strategy remains isolated so we can replace it without losing the working lifecycle concepts.

## Next milestone

**Phase 2 — Real market-data abstraction**

Target flow:

`Broker adapter → normalized market snapshot → feature engine → strategy engine`

The first implementation should support read-only market data and remain provider-agnostic, with Dhan as the first adapter.
