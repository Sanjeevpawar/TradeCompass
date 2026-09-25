from __future__ import annotations

from production.models import RiskSnapshot


def build_production_risk(
    analysis: dict,
    option: dict | None,
    direction: str | None,
    *,
    min_rr: float = 1.5,
    min_delta: float = 0.45,
    max_delta: float = 0.65,
    max_premium: float = 500.0,
) -> dict:
    rejects: list[str] = []
    warnings: list[str] = []
    if not analysis.get("valid"):
        rejects.append("Market analysis is invalid")
    if direction not in ("CALL", "PUT"):
        rejects.append("No directional setup")
    if not option or option.get("ltp") is None:
        rejects.append("No suggested option")
    if rejects:
        return RiskSnapshot(False, None, None, None, None, None, None, None, None, [], [], rejects).as_dict()

    premium = float(option["ltp"])
    if premium <= 0:
        rejects.append("Option premium must be positive")
    if premium > max_premium:
        rejects.append(f"Premium exceeds configured maximum {max_premium:.2f}")
    delta = option.get("delta")
    if delta is None or not min_delta <= abs(float(delta)) <= max_delta:
        rejects.append("Option delta is outside the configured selection range")
    if rejects:
        return RiskSnapshot(False, premium, None, None, None, None, None, None, None, [], [], rejects).as_dict()

    levels = analysis.get("levels", {})
    ind = analysis.get("indicators", {})
    spot = float(analysis["last_price"])
    vwap = ind.get("vwap")
    support = levels.get("support")
    resistance = levels.get("resistance")
    atr = float(ind.get("atr_14") or 50)

    if direction == "CALL":
        candidates = [(float(x), "support") for x in (support,) if x is not None and float(x) < spot]
        if vwap is not None and float(vwap) < spot:
            candidates.append((float(vwap), "VWAP"))
        if candidates:
            underlying_stop, basis = max(candidates, key=lambda x: x[0])
        else:
            underlying_stop, basis = spot - 1.5 * atr, "ATR fallback"
    else:
        candidates = [(float(x), "resistance") for x in (resistance,) if x is not None and float(x) > spot]
        if vwap is not None and float(vwap) > spot:
            candidates.append((float(vwap), "VWAP"))
        if candidates:
            underlying_stop, basis = min(candidates, key=lambda x: x[0])
        else:
            underlying_stop, basis = spot + 1.5 * atr, "ATR fallback"

    distance = abs(spot - underlying_stop)
    risk = max(premium * 0.05, distance * abs(float(delta)))
    stop = max(0.01, premium - risk)
    if stop >= premium:
        rejects.append("Could not establish a positive premium risk")
    reward = risk * min_rr
    target = premium + reward
    rr = reward / risk if risk > 0 else None
    if rr is None or rr < min_rr:
        rejects.append("Risk/reward is below the configured minimum")

    if basis == "ATR fallback":
        warnings.append("Stop is based on ATR because no meaningful structure/VWAP level was available")
    warnings.append("Premium stop is a first-order Delta approximation; monitoring must re-evaluate live option behaviour")

    return RiskSnapshot(
        approved=not rejects,
        entry=round(premium, 2),
        stop_loss=round(stop, 2),
        target=round(target, 2),
        risk=round(risk, 2),
        reward=round(reward, 2),
        risk_reward=round(rr, 2) if rr is not None else None,
        underlying_invalidation=round(underlying_stop, 2),
        stop_basis=basis,
        reasons=[f"Underlying invalidation: {underlying_stop:.2f}", f"Risk/reward meets minimum {min_rr:.2f}"],
        warnings=warnings,
        rejection_reasons=rejects,
    ).as_dict()
