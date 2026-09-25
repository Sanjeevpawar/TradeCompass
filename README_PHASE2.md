# TradeCompass — Phase 2: Market Data Foundation

Phase 2 introduces a provider-neutral, read-only market-data layer.

## What is now built

- Normalized `MarketSnapshot` and `OptionQuote` models.
- `MarketDataProvider` interface.
- Deterministic mock provider for development/tests.
- DhanHQ read-only adapter for market snapshots, expiries and option chains.
- Option-chain feature extraction: PCR, ATM strike, OI totals, median spread and liquidity candidates.
- `/market/v2` API endpoint.
- Environment-based provider switching.

## Provider switching

Default:

```text
TRADECOMPASS_DATA_PROVIDER=mock
```

Live Dhan:

```text
TRADECOMPASS_DATA_PROVIDER=dhan
DHAN_CLIENT_ID=...
DHAN_ACCESS_TOKEN=...
```

No order placement is implemented in this layer.

## Important

The Dhan adapter follows the current DhanHQ v2 Option Chain and Market Quote contracts. Dhan's Option Chain provides OI, Greeks, volume, LTP, bid/ask and IV; its market quote endpoints provide LTP/OHLC/quote data. The adapter intentionally keeps this read-only. See the official DhanHQ documentation before connecting live credentials.

## Next phase

Build the quantitative feature engine on top of the normalized data:

`Market data → candles/indicators → market structure → regime → setup detection`
