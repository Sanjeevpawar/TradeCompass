from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StrategySignal:
    signal: str
    setup: str
    direction: str | None
    strength: str
    score: int
    reasons: list[str]
    warnings: list[str]
    invalidation: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _trend_conditions(analysis: dict) -> tuple[bool, list[str]]:
    ind = analysis.get("indicators", {})
    struct = analysis.get("structure", {})
    reasons: list[str] = []
    if ind.get("ema_5") and ind.get("ema_20") and ind.get("ema_50") and ind["ema_5"] > ind["ema_20"] > ind["ema_50"]:
        reasons.append("EMA 5 > EMA 20 > EMA 50")
    if ind.get("vwap") is not None and analysis.get("last_price", 0) > ind["vwap"]:
        reasons.append("price above VWAP")
    if struct.get("trend") in ("BULLISH", "MIXED_BULLISH"):
        reasons.append("bullish market structure")
    return len(reasons) >= 3, reasons


def _bear_conditions(analysis: dict) -> tuple[bool, list[str]]:
    ind = analysis.get("indicators", {})
    struct = analysis.get("structure", {})
    reasons: list[str] = []
    if ind.get("ema_5") and ind.get("ema_20") and ind.get("ema_50") and ind["ema_5"] < ind["ema_20"] < ind["ema_50"]:
        reasons.append("EMA 5 < EMA 20 < EMA 50")
    if ind.get("vwap") is not None and analysis.get("last_price", 0) < ind["vwap"]:
        reasons.append("price below VWAP")
    if struct.get("trend") in ("BEARISH", "MIXED_BEARISH"):
        reasons.append("bearish market structure")
    return len(reasons) >= 3, reasons


def evaluate_buying_setups(analysis: dict) -> list[dict]:
    """Deterministic setup validation. It never selects an option or places an order."""
    if not analysis.get("valid"):
        return [StrategySignal("WAIT", "NONE", None, "NONE", 0, [], [analysis.get("reason", "Invalid market data")], "No trade").as_dict()]

    regime = analysis.get("regime")
    indicators = analysis.get("indicators", {})
    setups = analysis.get("setups", [])
    results = []

    bullish_ok, bull_reasons = _trend_conditions(analysis)
    bearish_ok, bear_reasons = _bear_conditions(analysis)
    volume_ratio = indicators.get("volume_ratio")
    rsi = indicators.get("rsi_14")

    for setup in setups:
        name = setup["name"]
        direction = setup["direction"]
        reasons = bull_reasons if direction == "CALL" else bear_reasons
        if name == "TREND_CONTINUATION" and ((direction == "CALL" and bullish_ok) or (direction == "PUT" and bearish_ok)):
            warnings = []
            if volume_ratio is not None and volume_ratio < 1.0:
                warnings.append("volume is below average")
            if rsi is not None and ((direction == "CALL" and rsi >= 72) or (direction == "PUT" and rsi <= 28)):
                warnings.append("momentum may be extended")
            score = min(100, 50 + 10 * len(reasons) + (10 if (volume_ratio or 0) >= 1.2 else 0))
            results.append(StrategySignal("BUY_CALL" if direction == "CALL" else "BUY_PUT", name, direction, "STRONG" if score >= 80 else "MODERATE", score, reasons, warnings, "Break of the current structure/VWAP invalidates the setup").as_dict())
        elif name in ("BREAKOUT", "BREAKDOWN"):
            # Existing detector already requires volume expansion; require a directional regime too.
            regime_ok = (direction == "CALL" and regime == "BULLISH_TREND") or (direction == "PUT" and regime == "BEARISH_TREND")
            if regime_ok:
                score = min(100, 60 + 10 * len(reasons))
                results.append(StrategySignal("BUY_CALL" if direction == "CALL" else "BUY_PUT", name, direction, "STRONG" if score >= 80 else "MODERATE", score, reasons + setup.get("conditions", []), [], "Return below breakout/support level invalidates the setup").as_dict())

    if not results:
        return [StrategySignal("WAIT", "NONE", None, "NONE", 0, [], ["No validated option-buying setup"], "No trade").as_dict()]
    return sorted(results, key=lambda x: x["score"], reverse=True)
