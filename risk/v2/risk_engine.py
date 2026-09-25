from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskConfig:
    capital: float = 100_000.0
    risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 2.0
    max_trades_per_day: int = 3
    min_rr: float = 1.5
    lot_size: int = 65
    max_premium: float = 500.0
    min_delta: float = 0.45
    max_delta: float = 0.65
    max_spread_pct: float = 2.0

    @property
    def risk_amount(self) -> float:
        return self.capital * self.risk_per_trade_pct / 100.0


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    entry: float | None
    stop: float | None
    target: float | None
    rr: float | None
    quantity: int
    lots: int
    risk_amount: float
    max_loss: float | None
    reasons: list[str]
    warnings: list[str]
    rejection_reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _round_price(value: float) -> float:
    return round(float(value), 2)




def calculate_trade_risk(
    analysis: dict,
    premium: float,
    delta: float | None,
    direction: str,
    *,
    capital: float,
    risk_per_trade_pct: float = 1.0,
    min_rr: float = 1.5,
    lot_size: int = 65,
) -> dict:
    """Calculate the shared underlying invalidation, premium stop, target and size.

    This is the single deterministic risk calculation used by both live risk
    decisions and the historical backtester. ``direction`` accepts CALL/PUT
    (and CE/PE) so callers can use their native terminology.
    """
    premium = float(premium)
    if premium <= 0:
        return {"valid": False, "reason": "Option premium must be positive"}

    levels = analysis.get("levels", {})
    indicators = analysis.get("indicators", {})
    last = float(analysis.get("last_price"))
    vwap = indicators.get("vwap")
    support = levels.get("support")
    resistance = levels.get("resistance")
    direction = str(direction).upper()

    if direction in ("CALL", "CE"):
        candidates = [x for x in (support, vwap) if x is not None and float(x) < last]
        underlying_stop = max(
            map(float, candidates),
            default=last - 1.5 * float(indicators.get("atr_14") or 50),
        )
    elif direction in ("PUT", "PE"):
        candidates = [x for x in (resistance, vwap) if x is not None and float(x) > last]
        underlying_stop = min(
            map(float, candidates),
            default=last + 1.5 * float(indicators.get("atr_14") or 50),
        )
    else:
        return {"valid": False, "reason": f"Unsupported direction: {direction}"}

    underlying_distance = abs(last - underlying_stop)
    if underlying_distance <= 0:
        return {"valid": False, "reason": "Could not establish a positive underlying stop distance"}

    abs_delta = abs(float(delta)) if delta is not None else 0.55
    premium_loss = underlying_distance * abs_delta
    premium_stop = max(0.05 * premium, premium - premium_loss)
    premium_stop = min(premium - 0.01, premium_stop)
    if premium_stop <= 0:
        premium_stop = premium * 0.5

    risk_per_unit = premium - premium_stop
    if risk_per_unit <= 0:
        return {"valid": False, "reason": "Premium stop produces no positive risk"}

    target = premium + risk_per_unit * min_rr
    rr = (target - premium) / risk_per_unit
    risk_budget = float(capital) * float(risk_per_trade_pct) / 100.0
    lots = int(risk_budget // (risk_per_unit * lot_size)) if lot_size else 0
    quantity = lots * lot_size
    actual_risk = risk_per_unit * quantity

    return {
        "valid": quantity >= lot_size and rr + 1e-9 >= min_rr,
        "underlying_stop": underlying_stop,
        "underlying_distance": underlying_distance,
        "premium_stop": premium_stop,
        "target": target,
        "risk_per_unit": risk_per_unit,
        "rr": rr,
        "risk_budget": risk_budget,
        "lots": lots,
        "quantity": quantity,
        "actual_risk": actual_risk,
        "reason": (
            "Risk budget cannot support one lot at the calculated stop"
            if quantity < lot_size else None
        ),
    }


def build_risk_decision(
    analysis: dict,
    option: dict | None,
    config: RiskConfig,
) -> dict:
    """Validate a directional option-buying setup using deterministic risk rules.

    Stops are anchored to the underlying structure/VWAP, then translated into an
    option-premium stop using a configurable proxy. This is intentionally a
    decision-support calculation, not an order-placement function.
    """
    reasons: list[str] = []
    warnings: list[str] = []
    rejects: list[str] = []

    if not analysis.get("valid"):
        rejects.append("Invalid market analysis")
    if not option or option.get("ltp") is None:
        rejects.append("No valid option candidate")

    if rejects:
        return RiskDecision(False, None, None, None, None, 0, 0, 0.0, None, reasons, warnings, rejects).as_dict()

    premium = float(option["ltp"])
    if premium <= 0:
        rejects.append("Option premium must be positive")
    if premium > config.max_premium:
        rejects.append(f"Premium {premium:.2f} exceeds configured maximum {config.max_premium:.2f}")

    delta = option.get("delta")
    if delta is not None and not (config.min_delta <= abs(float(delta)) <= config.max_delta):
        rejects.append(f"Delta {abs(float(delta)):.2f} is outside configured range {config.min_delta:.2f}-{config.max_delta:.2f}")

    spread = option.get("spread")
    if spread is not None and premium > 0:
        spread_pct = abs(float(spread)) / premium * 100
        if spread_pct > config.max_spread_pct:
            rejects.append(f"Bid/ask spread {spread_pct:.2f}% exceeds {config.max_spread_pct:.2f}%")

    direction = option.get("option_type")
    trade_risk = calculate_trade_risk(
        analysis, premium, delta, direction,
        capital=config.capital,
        risk_per_trade_pct=config.risk_per_trade_pct,
        min_rr=config.min_rr,
        lot_size=config.lot_size,
    )
    if not trade_risk.get("valid") and trade_risk.get("reason"):
        rejects.append(trade_risk["reason"])

    premium_stop = trade_risk.get("premium_stop")
    target = trade_risk.get("target")
    rr = trade_risk.get("rr")
    quantity = trade_risk.get("quantity", 0)
    lots = trade_risk.get("lots", 0)
    actual_risk = trade_risk.get("actual_risk", 0.0)
    risk_budget = trade_risk.get("risk_budget", config.risk_amount)
    underlying_stop = trade_risk.get("underlying_stop")
    risk_per_unit = trade_risk.get("risk_per_unit")
    vwap = analysis.get("indicators", {}).get("vwap")

    if rr is not None and rr + 1e-9 < config.min_rr:
        rejects.append(f"Risk/reward {rr:.2f} is below minimum {config.min_rr:.2f}")

    if not rejects:
        reasons.extend([
            f"Risk budget ₹{risk_budget:.2f}",
            f"Underlying invalidation near {underlying_stop:.2f}",
            f"Calculated premium risk ₹{risk_per_unit:.2f} per unit",
            f"Position size {lots} lot(s) / {quantity} quantity",
            f"Minimum risk/reward {rr:.2f} achieved",
        ])
        if vwap is not None:
            warnings.append("Premium stop is a proxy; final implementation should use live option repricing")

    return RiskDecision(
        approved=not rejects,
        entry=_round_price(premium),
        stop=_round_price(premium_stop),
        target=_round_price(target),
        rr=round(rr, 2) if rr is not None else None,
        quantity=quantity,
        lots=lots,
        risk_amount=round(actual_risk, 2) if not rejects else 0.0,
        max_loss=round(actual_risk, 2) if not rejects else None,
        reasons=reasons,
        warnings=warnings,
        rejection_reasons=rejects,
    ).as_dict()
