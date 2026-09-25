# TradeCompass Phase 11 — Live Read-Only Command Center

Phase 11 changes the immediate focus from long-running historical setup scanning to a live, read-only TradeCompass decision engine.

## What it does

For each newly completed 5-minute NIFTY candle, the engine:

1. Loads completed intraday candles from the configured provider.
2. Runs the existing deterministic quantitative/technical engine.
3. Fetches the active NIFTY option expiry and live option chain.
4. Builds deterministic chain evidence: Put/Call Interest, OI change, OI concentration, resistance/support distances, ATM IV and data quality.
5. Evaluates four separate approaches:
   - Technical
   - Technical + Chain
   - Chain Only
   - Full TradeCompass
6. Selects a suggested option where the approach has a directional signal.
7. Applies the existing shared risk engine only to Full TradeCompass.
8. Persists each approach's signal snapshot in SQLite.

## Safety

- No order-placement API exists in this phase.
- `execution_enabled` is always false.
- This is read-only / paper observation.
- OI is not labelled as definite option-writer activity.
- Chain-only thresholds are deterministic research rules, not validated profitability claims.
- The current phase does not use historical future data to generate live signals.

## Configuration

Set these in `.env` (never commit the file):

```text
TRADECOMPASS_DATA_PROVIDER=dhan
DHAN_CLIENT_ID=...
DHAN_ACCESS_TOKEN=...
TRADECOMPASS_UNDERLYING_SECURITY_ID=13
TRADECOMPASS_UNDERLYING_SEGMENT=IDX_I
TRADECOMPASS_LIVE_INTERVAL=5
TRADECOMPASS_LIVE_POLL_SECONDS=30
TRADECOMPASS_LIVE_DB=data/live/tradecompass_live.db
```

## Run the API

```powershell
py -m uvicorn api.app:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

The dashboard polls every 30 seconds, but the engine only creates a new signal snapshot when a new completed candle appears.

## CLI

One live evaluation:

```powershell
py -m scripts.run_live_tradecompass --once
```

Continuous read-only monitoring:

```powershell
py -m scripts.run_live_tradecompass --poll-seconds 30
```

## APIs

- `GET /live/v1` — latest completed-candle TradeCompass state.
- `GET /live/signals?limit=50` — persisted signal history.

## Research status

The four live approaches are now an observation system. Their rules have **not** been statistically validated as profitable. Historical backtesting remains available and can be resumed later without changing this live architecture.
