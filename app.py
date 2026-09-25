print("🔥 LOADED api/app.py FROM:", __file__)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data.market_data import (
    get_daily_market_data,
    get_spot_market_data,
    get_option_chain_data
)

from data.broker_adapter import get_live_option_ltp

from analysis.daily_chart import analyze_daily_chart
from analysis.spot_analysis import analyze_spot_context
from analysis.option_chain import analyze_option_chain

from strategy.strategy_selector import select_strategy
from strategy.strike_selector import select_strikes

from core.decision_builder import build_decision
from core.permission_engine import apply_user_permission
from core.entry_engine import apply_entry_premiums

from monitoring.monitoring_engine import monitor_trade
from monitoring.feed_engine import generate_feed
from monitoring.feed_adapter import build_market_snapshot
from data.market_service import get_v2_snapshot, get_quant_analysis
from data.providers.factory import get_market_data_provider
from analysis.v2.option_features import option_chain_features, select_liquid_candidates
from analysis.v2.quant_engine import analyze_market
from strategy.v2.buying_rules import evaluate_buying_setups
from strategy.v2.option_buying import select_buying_option
from risk.v2.risk_engine import RiskConfig, build_risk_decision
from live.engine import LiveTradeCompassEngine
from backtesting.v1.engine import BacktestConfig, run_backtest
from backtesting.v2.engine import ContractBacktestConfig, run_contract_backtest
from backtesting.v2.data_loader import load_option_bars_csv, load_underlying_csv

# 🔽 PHASE-9 IMPORTS (NEW)
from execution.paper_ledger import get_all_trades, get_trade_by_id

# -------------------------------------------------
# APP INIT
# -------------------------------------------------
app = FastAPI(title="TradeCompass API")

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.get("/")
def health():
    return {"status": "TradeCompass API running"}

# -------------------------------------------------
# TEMP IN-MEMORY STATE
# -------------------------------------------------
CURRENT_DECISION = None

# -------------------------------------------------
# API MODELS
# -------------------------------------------------
class UserResponse(BaseModel):
    response: str

# -------------------------------------------------
# 1️⃣ GET TRADE DECISION
# -------------------------------------------------
@app.get("/decision")
def get_decision():
    global CURRENT_DECISION

    daily_ctx = analyze_daily_chart(get_daily_market_data())
    spot_ctx = analyze_spot_context(get_spot_market_data())
    option_ctx = analyze_option_chain(get_option_chain_data())

    # 🔑 CRITICAL: propagate structure
    option_ctx["support"] = spot_ctx.get("support")
    option_ctx["resistance"] = spot_ctx.get("resistance")

    if daily_ctx["risk"] == "HIGH" or option_ctx["market_state"] == "dangerous":
        CURRENT_DECISION = {
            "action": "NO_TRADE",
            "status": "BLOCKED",
            "reason": "High risk market",
            "next_step": "WAIT"
        }
        return CURRENT_DECISION

    strategy_ctx = select_strategy(daily_ctx, spot_ctx, option_ctx)
    strike_ctx = select_strikes(strategy_ctx, option_ctx)

    CURRENT_DECISION = build_decision(
        daily_ctx,
        spot_ctx,
        option_ctx,
        strategy_ctx,
        strike_ctx
    )

    # Freeze structure for lifecycle
    CURRENT_DECISION["support"] = spot_ctx.get("support")
    CURRENT_DECISION["resistance"] = spot_ctx.get("resistance")
    CURRENT_DECISION["spot"] = spot_ctx.get("spot")

    return CURRENT_DECISION

# -------------------------------------------------
# 2️⃣ CONFIRM TRADE
# -------------------------------------------------
@app.post("/decision/confirm")
def confirm_decision(user_input: UserResponse):
    global CURRENT_DECISION
    CURRENT_DECISION = apply_user_permission(
        CURRENT_DECISION, user_input.response
    )
    return CURRENT_DECISION

# -------------------------------------------------
# 3️⃣ ENTRY PREMIUMS
# -------------------------------------------------
@app.post("/decision/entry")
def submit_entry_premiums(premiums: dict):
    global CURRENT_DECISION
    CURRENT_DECISION = apply_entry_premiums(CURRENT_DECISION, premiums)
    return CURRENT_DECISION

# -------------------------------------------------
# 4️⃣ MONITOR (LIVE DATA SOURCE)
# -------------------------------------------------
@app.get("/monitor")
def monitor():
    global CURRENT_DECISION

    if not CURRENT_DECISION or CURRENT_DECISION.get("status") != "ACTIVE":
        return {
            "action": "NO_MONITORING",
            "reason": "Trade not active"
        }

    snapshot = {
        "option_ltp": get_live_option_ltp(CURRENT_DECISION["legs"]),
        "max_profit": CURRENT_DECISION.get("max_profit"),
        "max_loss": CURRENT_DECISION.get("max_loss"),
    }

    return monitor_trade(CURRENT_DECISION, snapshot)

# -------------------------------------------------
# 🧾 PHASE-9: PAPER TRADE HISTORY API (NEW)
# -------------------------------------------------
@app.get("/paper/trades")
def paper_trades():
    trades = get_all_trades()
    return {
        "count": len(trades),
        "trades": trades
    }

@app.get("/paper/trades/{trade_id}")
def paper_trade_by_id(trade_id: int):
    trade = get_trade_by_id(trade_id)
    if not trade:
        return {"error": "Trade not found"}
    return trade


# -------------------------------------------------
# PHASE 2: REAL-MARKET-DATA ABSTRACTION
# -------------------------------------------------
@app.get("/market/v2")
def market_v2():
    """Provider-neutral market snapshot. Defaults to mock until Dhan is configured."""
    import os
    snapshot = get_v2_snapshot(
        os.getenv("TRADECOMPASS_UNDERLYING_SECURITY_ID", "13"),
        os.getenv("TRADECOMPASS_UNDERLYING_SEGMENT", "IDX_I"),
    )
    market = snapshot["market"]
    chain = snapshot["chain"]
    features = option_chain_features(chain)
    calls = select_liquid_candidates(chain, "CE")[:3]
    puts = select_liquid_candidates(chain, "PE")[:3]
    return {
        "provider": snapshot["provider"],
        "market": market.__dict__,
        "option_chain": features,
        "candidates": {
            "calls": [o.__dict__ | {"spread": o.spread, "oi_change": o.oi_change} for o in calls],
            "puts": [o.__dict__ | {"spread": o.spread, "oi_change": o.oi_change} for o in puts],
        },
    }

# -------------------------------------------------
# PHASE 3: QUANTITATIVE MARKET ANALYSIS
# -------------------------------------------------
@app.get("/analysis/v1")
def quantitative_analysis(interval: int = 5):
    import os
    return get_quant_analysis(
        os.getenv("TRADECOMPASS_UNDERLYING_SECURITY_ID", "13"),
        os.getenv("TRADECOMPASS_UNDERLYING_SEGMENT", "IDX_I"),
        interval,
    )


# -------------------------------------------------
# PHASE 4: OPTION-BUYING STRATEGY ENGINE
# -------------------------------------------------
@app.get("/strategy/v1")
def buying_strategy(interval: int = 5):
    import os
    snapshot = get_v2_snapshot(
        os.getenv("TRADECOMPASS_UNDERLYING_SECURITY_ID", "13"),
        os.getenv("TRADECOMPASS_UNDERLYING_SEGMENT", "IDX_I"),
    )
    provider = get_market_data_provider()
    candles = provider.get_intraday_candles(
        os.getenv("TRADECOMPASS_UNDERLYING_SECURITY_ID", "13"),
        os.getenv("TRADECOMPASS_UNDERLYING_SEGMENT", "IDX_I"),
        "INDEX", interval, 1
    )
    analysis = analyze_market(candles)
    setups = evaluate_buying_setups(analysis)
    primary = setups[0] if setups else {"signal": "WAIT"}
    candidate = None
    if primary.get("direction") in ("CALL", "PUT"):
        candidate = select_buying_option(snapshot["chain"], primary["direction"])
        if candidate is None:
            primary = dict(primary)
            primary["signal"] = "WAIT"
            primary["warnings"] = primary.get("warnings", []) + ["No liquid option candidate met the selection rules"]
    risk = build_risk_decision(analysis, candidate, RiskConfig()) if candidate and primary.get("signal") in ("BUY_CALL", "BUY_PUT") else build_risk_decision(analysis, None, RiskConfig())
    if primary.get("signal") in ("BUY_CALL", "BUY_PUT") and not risk["approved"]:
        primary = dict(primary)
        primary["signal"] = "WAIT"
        primary["warnings"] = primary.get("warnings", []) + risk["rejection_reasons"]
    return {"provider": snapshot["provider"], "market": snapshot["market"].__dict__, "analysis": analysis, "setups": setups, "selected_option": candidate, "risk": risk}

# -------------------------------------------------
# PHASE 5: RISK ENGINE
# -------------------------------------------------
@app.get("/backtest/v1")
def backtest_v1(interval: int = 5, days: int = 1):
    """Run the strategy engine over provider candles without look-ahead.

    With the mock provider this validates the backtester mechanics only.
    Real edge analysis requires historical underlying + historical option quotes.
    """
    import os
    provider = get_market_data_provider()
    candles = provider.get_intraday_candles(
        os.getenv("TRADECOMPASS_UNDERLYING_SECURITY_ID", "13"),
        os.getenv("TRADECOMPASS_UNDERLYING_SEGMENT", "IDX_I"),
        "INDEX", interval, days
    )
    result = run_backtest(candles, BacktestConfig())
    result["provider"] = os.getenv("TRADECOMPASS_DATA_PROVIDER", "mock")
    return result




@app.get("/backtest/v2")
def backtest_v2():
    """Automatically scan every eligible historical setup and replay it using real option bars.

    Configure TRADECOMPASS_HISTORICAL_UNDERLYING_CSV and
    TRADECOMPASS_HISTORICAL_OPTIONS_CSV. The engine finds setup occurrences,
    selects the contract using only data available at entry, and simulates the
    subsequent option path.
    """
    import os
    underlying_path = os.getenv("TRADECOMPASS_HISTORICAL_UNDERLYING_CSV")
    options_path = os.getenv("TRADECOMPASS_HISTORICAL_OPTIONS_CSV")
    if not underlying_path or not options_path:
        return {
            "valid": False,
            "reason": "Set TRADECOMPASS_HISTORICAL_UNDERLYING_CSV and TRADECOMPASS_HISTORICAL_OPTIONS_CSV to run the automatic contract-aware backtest",
        }
    candles = load_underlying_csv(underlying_path)
    option_bars = load_option_bars_csv(options_path)
    result = run_contract_backtest(candles, option_bars, ContractBacktestConfig())
    result["underlying_source"] = underlying_path
    result["option_source"] = options_path
    return result


@app.get("/risk/v1")
def risk_analysis(interval: int = 5):
    result = buying_strategy(interval)
    return {
        "provider": result["provider"],
        "market": result["market"],
        "signal": result["setups"][0] if result.get("setups") else {"signal": "WAIT"},
        "selected_option": result.get("selected_option"),
        "risk": result.get("risk"),
    }

# -------------------------------------------------
# 5️⃣ MARKET FEED
# -------------------------------------------------
@app.get("/feed")
def get_market_feed():
    daily_ctx = analyze_daily_chart(get_daily_market_data())
    spot_ctx = analyze_spot_context(get_spot_market_data())
    option_ctx = analyze_option_chain(get_option_chain_data())

    option_ctx["support"] = spot_ctx.get("support")
    option_ctx["resistance"] = spot_ctx.get("resistance")

    snapshot = build_market_snapshot(daily_ctx, spot_ctx, option_ctx)
    return {"items": generate_feed(snapshot)}

# -------------------------------------------------
# PHASE 11: LIVE TRADECOMPASS (READ-ONLY)
# -------------------------------------------------
LIVE_ENGINE = None

def get_live_engine():
    global LIVE_ENGINE
    if LIVE_ENGINE is None:
        LIVE_ENGINE = LiveTradeCompassEngine()
    return LIVE_ENGINE

@app.get("/live/v1")
def live_tradecompass():
    """Return the latest completed 5-minute live TradeCompass decision.

    Read-only: no broker order is created. The engine caches the current
    completed candle and recalculates only when a new completed candle arrives.
    """
    result = get_live_engine().snapshot()
    return result

@app.get("/live/signals")
def live_signal_history(limit: int = 50):
    return {"count": len(get_live_engine().recent_signals(limit)), "signals": get_live_engine().recent_signals(limit)}


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
app.mount(
    "/dashboard",
    StaticFiles(directory="static", html=True),
    name="dashboard"
)
