# TradeCompass — Phase 2: Market Data Foundation

Phase 2 introduces a provider-neutral, read-only market-data layer.

## What is now built

- Normalized `MarketSnapshot` and `OptionQuote` models.
- `MarketDataProvider` interface.
- Deterministic mock provider for development/tests.
- DhanHQ read-only adapter for market snapshots, expiries and option chains.
- TOTP-based Dhan authentication with automatic 24-hour access-token generation and local caching.
- Option-chain feature extraction: PCR, ATM strike, OI totals, median spread and liquidity candidates.
- `/market/v2` API endpoint.
- Environment-based provider switching.

## Provider switching

**Default:**

```text
TRADECOMPASS_DATA_PROVIDER=mock