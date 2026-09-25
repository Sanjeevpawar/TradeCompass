# TradeCompass Phase 7 — Contract-Aware Historical Backtesting

Phase 7 upgrades the development backtester from a synthetic option-premium proxy to historical option-contract data.

## What it does automatically

1. Scans every historical underlying candle after the indicator warm-up period.
2. Detects the same BUY_CALL / BUY_PUT setups used by the strategy engine.
3. Uses the next underlying candle as the actionable entry point, preventing look-ahead.
4. At that exact timestamp, evaluates historical option contracts using only information available then.
5. Selects a contract using Delta, premium, spread, volume and expiry/DTE constraints.
6. Simulates the selected option's actual future OHLC path.
7. Applies stop, target, time exit, slippage and transaction costs.
8. Reports overall and per-setup statistics, including skipped setups caused by missing/invalid historical contracts.

## Historical option CSV

Required columns:

`timestamp,expiry,strike,option_type,open,high,low,close`

Optional columns:

`volume,iv,delta,theta,gamma,vega,bid,ask,spot`

`option_type` should be `CE` or `PE`.

## Run

Set:

```text
TRADECOMPASS_HISTORICAL_UNDERLYING_CSV=/path/underlying.csv
TRADECOMPASS_HISTORICAL_OPTIONS_CSV=/path/options.csv
```

Then call:

`GET /backtest/v2`

The result contains setup-level statistics and every simulated trade, including the selected strike and the alternatives that were considered.

## Important

This is research/backtesting output, not a guarantee of future performance. Before real-money use, add out-of-sample and walk-forward validation, realistic execution assumptions, and paper trading.
