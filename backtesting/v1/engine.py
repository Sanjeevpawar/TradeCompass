from __future__ import annotations

from dataclasses import dataclass, asdict
from math import isfinite
from typing import Iterable

from data.candle_models import Candle
from analysis.v2.quant_engine import analyze_market
from strategy.v2.buying_rules import evaluate_buying_setups


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    risk_per_trade_pct: float = 1.0
    max_bars_in_trade: int = 12
    slippage_pct: float = 0.05
    transaction_cost_pct: float = 0.02
    option_delta: float = 0.55
    option_multiplier: int = 1
    min_signal_score: int = 70


@dataclass
class BacktestTrade:
    entry_time: str
    exit_time: str
    direction: str
    setup: str
    signal_score: int
    underlying_entry: float
    underlying_exit: float
    option_entry: float
    option_exit: float
    quantity: int
    pnl: float
    pnl_pct: float
    r_multiple: float
    exit_reason: str


class UnderlyingProxyOptionModel:
    """Deterministic option-premium proxy for development only.

    This is NOT a substitute for historical option-chain data. It provides a
    pluggable interface so the backtester can be upgraded to real historical
    option quotes without rewriting the execution loop.
    """

    def __init__(self, delta: float = 0.55):
        self.delta = abs(delta)

    def premium(self, underlying: float, reference: float, entry_premium: float, direction: str) -> float:
        move = underlying - reference
        signed = move if direction == "CALL" else -move
        return max(0.05, entry_premium + signed * self.delta)


def _option_entry_premium(spot: float) -> float:
    # Synthetic ATM-ish starting premium. Replaced by actual option quote later.
    return max(20.0, spot * 0.008)


def _apply_costs(gross_pnl: float, entry_value: float, exit_value: float, cfg: BacktestConfig) -> float:
    slippage = (entry_value + exit_value) * cfg.slippage_pct / 100.0
    costs = (entry_value + exit_value) * cfg.transaction_cost_pct / 100.0
    return gross_pnl - slippage - costs


def run_backtest(candles: Iterable[Candle], config: BacktestConfig | None = None) -> dict:
    cfg = config or BacktestConfig()
    candles = list(candles)
    if len(candles) < 35:
        return {"valid": False, "reason": f"Need at least 35 candles; received {len(candles)}", "trades": [], "metrics": {}}

    capital = cfg.initial_capital
    peak = capital
    max_drawdown = 0.0
    trades: list[dict] = []
    model = UnderlyingProxyOptionModel(cfg.option_delta)
    i = 30

    while i < len(candles) - 1:
        analysis = analyze_market(candles[: i + 1])
        setups = evaluate_buying_setups(analysis)
        signal = next((s for s in setups if s["signal"] in ("BUY_CALL", "BUY_PUT") and s["score"] >= cfg.min_signal_score), None)
        if not signal:
            i += 1
            continue

        # No look-ahead: signal is formed on candle i, entry is next candle open.
        entry_bar = candles[i + 1]
        direction = signal["direction"]
        underlying_entry = entry_bar.open
        entry_premium = _option_entry_premium(underlying_entry)
        risk_per_unit = max(entry_premium * 0.20, 1.0)
        risk_budget = capital * cfg.risk_per_trade_pct / 100.0
        quantity = max(1, int(risk_budget / risk_per_unit)) * cfg.option_multiplier

        entry_value = entry_premium * quantity
        exit_bar = None
        exit_reason = "TIME_EXIT"
        option_exit = None
        bars_held = 0

        # Use the strategy's underlying invalidation level when available.
        levels = analysis.get("levels", {})
        if direction == "CALL":
            stop_level = float(levels.get("support") or analysis["last_price"] - (analysis["indicators"].get("atr_14") or 50))
        else:
            stop_level = float(levels.get("resistance") or analysis["last_price"] + (analysis["indicators"].get("atr_14") or 50))

        target_move = abs(analysis["last_price"] - stop_level) * 1.5
        target_level = underlying_entry + target_move if direction == "CALL" else underlying_entry - target_move

        exit_index = None
        for j in range(i + 1, min(len(candles), i + 1 + cfg.max_bars_in_trade)):
            bar = candles[j]
            bars_held += 1
            if direction == "CALL":
                stop_hit = bar.low <= stop_level
                target_hit = bar.high >= target_level
            else:
                stop_hit = bar.high >= stop_level
                target_hit = bar.low <= target_level

            if stop_hit:
                exit_bar = bar
                exit_reason = "STOP"
                underlying_exit = stop_level
                exit_index = j
                break
            if target_hit:
                exit_bar = bar
                exit_reason = "TARGET"
                underlying_exit = target_level
                exit_index = j
                break

        if exit_bar is None:
            exit_bar = candles[min(len(candles) - 1, i + cfg.max_bars_in_trade)]
            underlying_exit = exit_bar.close

        option_exit = model.premium(underlying_exit, underlying_entry, entry_premium, direction)
        exit_value = option_exit * quantity
        gross_pnl = (option_exit - entry_premium) * quantity
        pnl = _apply_costs(gross_pnl, entry_value, exit_value, cfg)
        capital += pnl
        peak = max(peak, capital)
        drawdown = (peak - capital) / peak * 100 if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        risk_amount = risk_per_unit * quantity
        r_multiple = pnl / risk_amount if risk_amount else 0.0
        pnl_pct = pnl / entry_value * 100 if entry_value else 0.0

        trade = BacktestTrade(
            entry_time=entry_bar.timestamp,
            exit_time=exit_bar.timestamp,
            direction=direction,
            setup=signal["setup"],
            signal_score=signal["score"],
            underlying_entry=round(underlying_entry, 2),
            underlying_exit=round(underlying_exit, 2),
            option_entry=round(entry_premium, 2),
            option_exit=round(option_exit, 2),
            quantity=quantity,
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            r_multiple=round(r_multiple, 2),
            exit_reason=exit_reason,
        )
        trades.append(asdict(trade))
        i = (exit_index + 1) if exit_index is not None else min(len(candles), i + cfg.max_bars_in_trade + 1)

    pnls = [t["pnl"] for t in trades]
    winners = [x for x in pnls if x > 0]
    losers = [x for x in pnls if x < 0]
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers))
    total = len(trades)
    win_rate = len(winners) / total * 100 if total else 0.0
    expectancy = sum(pnls) / total if total else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0)

    return {
        "valid": True,
        "config": asdict(cfg),
        "metrics": {
            "initial_capital": cfg.initial_capital,
            "ending_capital": round(capital, 2),
            "net_pnl": round(capital - cfg.initial_capital, 2),
            "total_trades": total,
            "wins": len(winners),
            "losses": len(losers),
            "win_rate_pct": round(win_rate, 2),
            "expectancy_per_trade": round(expectancy, 2),
            "profit_factor": round(profit_factor, 3) if isfinite(profit_factor) else None,
            "max_drawdown_pct": round(max_drawdown, 2),
            "avg_r": round(sum(t["r_multiple"] for t in trades) / total, 2) if total else 0.0,
            "target_exits": sum(t["exit_reason"] == "TARGET" for t in trades),
            "stop_exits": sum(t["exit_reason"] == "STOP" for t in trades),
            "time_exits": sum(t["exit_reason"] == "TIME_EXIT" for t in trades),
        },
        "trades": trades,
        "data_note": "Results use a synthetic option-premium proxy. They are for engine validation only, not evidence of trading edge.",
    }
