# TradeCompass Phase 8 — Dhan Historical Data Integration

## Validated locally

The Dhan connection has been tested with the user's account:

- `/v2/profile` returns HTTP 200 and the Data API is active.
- NIFTY (`securityId=13`, `IDX_I`) 5-minute historical candles return successfully.
- Dhan rolling expired-options data returns successfully with `expiryCode=1`.
- The option response contains OHLC, IV, volume, strike, OI and spot arrays.

Dhan's current documentation describes the rolling endpoint as relative-strike historical data (ATM through permitted relative strikes), up to 5 years, with OHLC, IV, volume, OI and spot. The endpoint does **not** return an explicit expiry-date field in the response example. Therefore this phase deliberately does not invent an expiry date.

## Important backtesting limitation

The existing Phase 7 selector expects an explicit expiry date, Delta and bid/ask spread. Dhan's rolling historical endpoint provides IV/OI/strike/spot but not Delta, bid or ask, and its response is rolling by relative strike. Therefore we should **not** blindly feed this response into the existing contract selector yet.

The next integration step is to build a Dhan historical contract layer that:

1. preserves the actual absolute strike returned at each timestamp;
2. maps the selected rolling contract to its actual expiry using an auditable expiry-calendar source;
3. calculates Delta from spot, strike, IV and time-to-expiry rather than fabricating it;
4. treats unavailable historical bid/ask as unavailable instead of assuming a zero spread;
5. verifies the selected contract's future bars before allowing a backtest trade.

This is intentionally conservative to prevent look-ahead bias and false backtest results.

## Environment

`.env` should contain:

```text
DHAN_ACCESS_TOKEN=your_token
TRADECOMPASS_DHAN_EXPIRY_CODE=1
```

The user's token must remain local and must never be committed to Git or pasted into chat.
