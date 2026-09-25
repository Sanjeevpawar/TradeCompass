from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo

from analysis.v2.quant_engine import analyze_market
from data.market_models import OptionChainSnapshot
from data.providers.factory import get_market_data_provider
from risk.v2.risk_engine import RiskConfig, build_risk_decision
from strategy.v2.buying_rules import evaluate_buying_setups
from strategy.v2.option_buying import select_buying_option
from .chain_signals import build_live_chain_context
from .signal_store import SignalStore


IST = ZoneInfo("Asia/Kolkata")


def _parse_timestamp(value: str) -> datetime:
    text = str(value)
    try:
        dt = datetime.fromtimestamp(float(text), tz=timezone.utc)
        return dt.astimezone(IST)
    except (ValueError, TypeError):
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt.astimezone(IST)


def _completed_candles(candles, interval_minutes: int):
    now = datetime.now(IST)
    completed = []
    for candle in candles:
        start = _parse_timestamp(candle.timestamp)
        if start + timedelta(minutes=interval_minutes) <= now:
            completed.append(candle)
    return completed


def _technical_result(analysis: dict) -> dict:
    setups = evaluate_buying_setups(analysis)
    primary = setups[0] if setups else {"signal": "WAIT", "setup": "NONE", "score": 0}
    direction = primary.get("direction")
    return {
        "signal": primary.get("signal", "WAIT"),
        "direction": direction,
        "setup": primary.get("setup", "NONE"),
        "score": primary.get("score", 0),
        "strength": primary.get("strength", "NONE"),
        "reasons": primary.get("reasons", []),
        "warnings": primary.get("warnings", []),
        "invalidation": primary.get("invalidation"),
        "all_setups": setups,
        "spot": analysis.get("last_price"),
    }


def _chain_compatibility(technical: dict, chain_ctx: dict) -> dict:
    ts = technical.get("signal", "WAIT")
    cs = chain_ctx.get("signal", "WAIT")
    if ts in ("BUY_CALL", "BUY_PUT") and ts == cs:
        signal = ts
        status = "SUPPORTED"
        reason = "Technical direction and option-chain direction agree"
    elif cs == "WAIT":
        signal = "WAIT"
        status = "MIXED"
        reason = "Option-chain evidence is not decisive"
    elif ts in ("BUY_CALL", "BUY_PUT") and cs in ("BUY_CALL", "BUY_PUT") and ts != cs:
        signal = "WAIT"
        status = "CONFLICT"
        reason = "Technical and option-chain directions conflict"
    else:
        signal = "WAIT"
        status = "NO_SETUP"
        reason = "No technical setup to confirm"
    return {"signal": signal, "status": status, "reason": reason}


class LiveTradeCompassEngine:
    def __init__(self):
        self.provider = get_market_data_provider()
        self.security_id = os.getenv("TRADECOMPASS_UNDERLYING_SECURITY_ID", "13")
        self.segment = os.getenv("TRADECOMPASS_UNDERLYING_SEGMENT", "IDX_I")
        self.interval = int(os.getenv("TRADECOMPASS_LIVE_INTERVAL", "5"))
        self.store = SignalStore(os.getenv("TRADECOMPASS_LIVE_DB", "data/live/tradecompass_live.db"))
        self._lock = Lock()
        self._last_timestamp = None
        self._cached = None
        self._expiry = None
        self._previous_chain: OptionChainSnapshot | None = None

    def _get_chain(self) -> OptionChainSnapshot:
        expiries = self.provider.get_expiries(self.security_id, self.segment)
        if not expiries:
            raise RuntimeError("Dhan returned no active NIFTY expiry")
        expiry = expiries[0]
        self._expiry = expiry
        return self.provider.get_option_chain(self.security_id, self.segment, expiry)

    def _option_for(self, chain, direction):
        if direction not in ("CALL", "PUT"):
            return None
        return select_buying_option(chain, direction)

    def _build(self):
        candles = self.provider.get_intraday_candles(
            self.security_id, self.segment, "INDEX", self.interval, 1
        )
        candles = _completed_candles(candles, self.interval)
        if len(candles) < 30:
            raise RuntimeError(f"Need at least 30 completed candles; received {len(candles)}")

        last = candles[-1]
        timestamp = last.timestamp
        if timestamp == self._last_timestamp and self._cached is not None:
            return self._cached

        analysis = analyze_market(candles)
        technical = _technical_result(analysis)
        chain = self._get_chain()
        chain_ctx = build_live_chain_context(chain)
        compatibility = _chain_compatibility(technical, chain_ctx)

        technical_option = self._option_for(chain, technical.get("direction"))
        chain_direction = "CALL" if chain_ctx["signal"] == "BUY_CALL" else "PUT" if chain_ctx["signal"] == "BUY_PUT" else None
        chain_option = self._option_for(chain, chain_direction)

        tc_direction = "CALL" if compatibility["signal"] == "BUY_CALL" else "PUT" if compatibility["signal"] == "BUY_PUT" else None
        tc_option = self._option_for(chain, tc_direction)

        risk = build_risk_decision(analysis, tc_option, RiskConfig()) if tc_option else build_risk_decision(analysis, None, RiskConfig())
        full_signal = compatibility["signal"] if risk.get("approved") else "WAIT"
        full_reason = compatibility["reason"] if full_signal != "WAIT" else (
            "Risk gate rejected the setup" if compatibility["signal"] != "WAIT" else compatibility["reason"]
        )

        technical_view = {**technical, "suggested_option": technical_option}
        chain_view = {
            "signal": chain_ctx["signal"], "direction": chain_direction,
            "setup": "CHAIN_CONTEXT", "score": chain_ctx["evidence_score"],
            "spot": chain.underlying_ltp, "reasons": chain_ctx["bullish_evidence"] if chain_ctx["signal"] == "BUY_CALL" else chain_ctx["bearish_evidence"],
            "suggested_option": chain_option, "evidence": chain_ctx,
        }
        tech_chain_view = {
            **compatibility, "direction": "CALL" if compatibility["signal"] == "BUY_CALL" else "PUT" if compatibility["signal"] == "BUY_PUT" else None,
            "spot": chain.underlying_ltp, "suggested_option": tc_option, "evidence": chain_ctx,
            "technical": technical,
        }
        full_view = {
            "signal": full_signal,
            "direction": tc_direction if full_signal != "WAIT" else None,
            "setup": technical.get("setup", "NONE"),
            "spot": chain.underlying_ltp,
            "suggested_option": tc_option if full_signal != "WAIT" else None,
            "risk": risk,
            "reason": full_reason,
            "technical_chain_status": compatibility["status"],
        }

        result = {
            "valid": True,
            "timestamp": timestamp,
            "timestamp_ist": _parse_timestamp(timestamp).isoformat(),
            "provider": self.provider.__class__.__name__,
            "interval_minutes": self.interval,
            "market": {
                "symbol": "NIFTY",
                "spot": chain.underlying_ltp,
                "candle_open": last.open,
                "candle_high": last.high,
                "candle_low": last.low,
                "candle_close": last.close,
                "candle_volume": last.volume,
            },
            "analysis": analysis,
            "chain": chain_ctx,
            "approaches": {
                "technical": technical_view,
                "technical_plus_chain": tech_chain_view,
                "chain_only": chain_view,
                "full_tradecompass": full_view,
            },
            "live_mode": "READ_ONLY_PAPER_OBSERVATION",
            "execution_enabled": False,
        }

        for name, view in result["approaches"].items():
            self.store.record(candle_timestamp=timestamp, approach=name, result=view)

        self._last_timestamp = timestamp
        self._cached = result
        self._previous_chain = chain
        return result

    def snapshot(self):
        with self._lock:
            return self._build()

    def recent_signals(self, limit=50):
        return self.store.recent(limit)
