# TradeCompass — Phase 3: Quantitative Engine

Phase 3 adds a deterministic quantitative analysis layer on top of the normalized market-data provider.

## What is now built

- Normalized intraday candle model.
- Provider interface now supports intraday candles.
- Mock 5-minute candle stream for deterministic development/testing.
- DhanHQ v2 intraday chart adapter (read-only).
- Indicator engine:
  - EMA 5/20/50
  - SMA 100/200 when enough history is available
  - RSI 14
  - ATR 14
  - VWAP
  - MACD
  - volume ratio
- Market structure engine:
  - higher high / higher low
  - lower high / lower low
  - trend classification
  - support/resistance
- Regime engine:
  - BULLISH_TREND
  - BEARISH_TREND
  - RANGE_BOUND
  - TRANSITION
- Initial deterministic setup detector:
  - trend continuation
  - breakout
  - breakdown
- New API: `GET /analysis/v1?interval=5`

## Important design rule

This phase does not produce a trading order and does not claim a probability of success. It produces structured market facts and setup candidates for later strategy/risk layers.

## Next phase

Build the option-buying strategy engine:

`Quantitative analysis → setup validation → CALL/PUT decision → option selector`
