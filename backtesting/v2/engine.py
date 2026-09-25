from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import defaultdict
from typing import Callable

from analysis.v2.quant_engine import analyze_market
from strategy.v2.buying_rules import evaluate_buying_setups
from backtesting.v2.models import HistoricalOptionBar
from backtesting.v2.option_selector import select_historical_option
from data.candle_models import Candle
from risk.v2.risk_engine import calculate_trade_risk


@dataclass(frozen=True)
class ContractBacktestConfig:
    initial_capital: float = 100_000.0
    risk_per_trade_pct: float = 1.0
    min_signal_score: int = 70
    min_rr: float = 1.5
    max_bars_in_trade: int = 12
    min_delta: float = 0.45
    max_delta: float = 0.65
    target_delta: float = 0.55
    max_spread_pct: float = 2.0
    require_spread_data: bool = True
    max_premium: float = 500.0
    min_volume: int = 1
    min_dte: int = 1
    max_dte: int = 14
    lot_size: int = 65
    slippage_pct: float = 0.05
    transaction_cost_pct: float = 0.02
    require_full_horizon: bool = True


def _series_for_contract(bars: list[HistoricalOptionBar], selected: dict) -> list[HistoricalOptionBar]:
    return sorted(
        [
            b for b in bars
            if b.expiry == selected["expiry"]
            and b.strike == selected["strike"]
            and b.option_type == selected["option_type"]
        ],
        key=lambda x: x.timestamp,
    )


def _cost(gross: float, entry: float, exit_: float, qty: int, cfg: ContractBacktestConfig) -> float:
    turnover = (entry + exit_) * qty
    return gross - turnover * (cfg.slippage_pct + cfg.transaction_cost_pct) / 100.0


def _has_full_horizon(series: list[HistoricalOptionBar], entry_idx: int, max_bars: int) -> bool:
    """Require every future option bar needed for the configured holding window."""
    required = max_bars + 1  # entry bar + max_bars future bars
    return len(series) - entry_idx >= required


def run_contract_backtest(
    candles: list[Candle],
    option_bars: list[HistoricalOptionBar],
    config: ContractBacktestConfig | None = None,
    progress_callback: Callable[[dict], None] | None = None,
    progress_interval: int = 100,
) -> dict:
    cfg = config or ContractBacktestConfig()
    if progress_interval < 1:
        raise ValueError("progress_interval must be >= 1")
    if len(candles) < 35:
        return {"valid": False, "reason": f"Need at least 35 underlying candles; received {len(candles)}", "trades": [], "metrics": {}}
    if not option_bars:
        return {"valid": False, "reason": "No historical option bars supplied", "trades": [], "metrics": {}}

    capital = cfg.initial_capital
    peak = capital
    max_dd = 0.0
    trades = []
    skipped = defaultdict(int)
    candle_index = {c.timestamp: idx for idx, c in enumerate(candles)}
    i = 30
    decision_total = max(0, len(candles) - 31)
    decision_processed = 0
    iterations = 0
    signals_detected = 0

    def emit_progress(force: bool = False) -> None:
        if progress_callback is None:
            return
        if not force and iterations % progress_interval != 0:
            return
        pct = (decision_processed / decision_total * 100.0) if decision_total else 100.0
        progress_callback({
            "processed": decision_processed,
            "total": decision_total,
            "percent": round(pct, 2),
            "current_index": min(i, len(candles) - 1),
            "current_timestamp": candles[min(i, len(candles) - 1)].timestamp if candles else None,
            "signals": signals_detected,
            "trades": len(trades),
            "skipped": dict(skipped),
        })

    while i < len(candles) - 1:
        iterations += 1
        decision_processed = max(0, min(i - 30 + 1, decision_total))
        emit_progress()
        analysis = analyze_market(candles[:i + 1])
        setups = evaluate_buying_setups(analysis)
        signal = next((s for s in setups if s["signal"] in ("BUY_CALL", "BUY_PUT") and s["score"] >= cfg.min_signal_score), None)
        if signal:
            signals_detected += 1
        if not signal:
            i += 1
            continue

        entry_bar = candles[i + 1]
        selection = select_historical_option(
            option_bars,
            entry_bar.timestamp,
            signal["direction"],
            selection_timestamp=candles[i].timestamp,
            min_delta=cfg.min_delta, max_delta=cfg.max_delta, target_delta=cfg.target_delta,
            max_spread_pct=cfg.max_spread_pct, require_spread_data=cfg.require_spread_data,
            max_premium=cfg.max_premium, min_volume=cfg.min_volume,
            min_dte=cfg.min_dte, max_dte=cfg.max_dte,
        )
        if not selection.get("selected"):
            skipped["no_contract"] += 1
            i += 1
            continue

        selected = selection["selected"]
        series = _series_for_contract(option_bars, selected)
        entry_idx = next((k for k, b in enumerate(series) if b.timestamp == entry_bar.timestamp), None)
        if entry_idx is None:
            skipped["no_future_series"] += 1
            i += 1
            continue

        if cfg.require_full_horizon and not _has_full_horizon(series, entry_idx, cfg.max_bars_in_trade):
            skipped["insufficient_future_contract_bars"] += 1
            i += 1
            continue

        entry_option = series[entry_idx]
        entry = entry_option.open
        if entry <= 0:
            skipped["invalid_entry"] += 1
            i += 1
            continue

        delta = abs(selected.get("delta") or cfg.target_delta)
        trade_risk = calculate_trade_risk(
            analysis, entry, delta, signal["direction"],
            capital=capital,
            risk_per_trade_pct=cfg.risk_per_trade_pct,
            min_rr=cfg.min_rr,
            lot_size=cfg.lot_size,
        )
        if not trade_risk.get("valid"):
            skipped["invalid_risk"] += 1
            i += 1
            continue

        premium_stop = trade_risk["premium_stop"]
        target = trade_risk["target"]
        risk_per_unit = trade_risk["risk_per_unit"]
        lots = trade_risk["lots"]
        qty = trade_risk["quantity"]

        exit_bar = None
        exit_reason = "TIME_EXIT"
        exit_price = None
        max_j = entry_idx + 1 + cfg.max_bars_in_trade
        for j in range(entry_idx + 1, max_j):
            b = series[j]
            stop_hit = b.low <= premium_stop
            target_hit = b.high >= target
            if stop_hit:
                exit_bar, exit_price, exit_reason = b, premium_stop, "STOP"
                break
            if target_hit:
                exit_bar, exit_price, exit_reason = b, target, "TARGET"
                break
        if exit_bar is None:
            exit_bar = series[max_j - 1]
            exit_price = exit_bar.close

        gross = (exit_price - entry) * qty
        pnl = _cost(gross, entry, exit_price, qty, cfg)
        capital += pnl
        peak = max(peak, capital)
        max_dd = max(max_dd, (peak - capital) / peak * 100 if peak else 0)
        risk_amount = risk_per_unit * qty

        trades.append({
            "entry_time": entry_option.timestamp, "exit_time": exit_bar.timestamp,
            "direction": signal["direction"], "setup": signal["setup"], "signal_score": signal["score"],
            "expiry": selected["expiry"], "strike": selected["strike"], "option_type": selected["option_type"],
            "entry_premium": round(entry, 2), "entry_reference": "historical_option_open",
            "exit_premium": round(exit_price, 2), "stop_premium": round(premium_stop, 2),
            "target_premium": round(target, 2), "delta": selected["delta"], "iv": selected["iv"],
            "theta": selected["theta"], "volume": selected["volume"], "spread_pct": selected["spread_pct"],
            "spread_data_status": selected.get("spread_data_status", "UNKNOWN"), "dte": selected["dte"],
            "quantity": qty, "lots": lots, "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / (entry * qty) * 100, 2),
            "r_multiple": round(pnl / risk_amount, 2) if risk_amount else 0.0,
            "exit_reason": exit_reason, "selection_reason": selection["reason"],
            "alternatives": selection.get("alternatives", []),
        })
        exit_candle_index = candle_index.get(exit_bar.timestamp, i + 1)
        i = max(i + 1, exit_candle_index + 1)

    decision_processed = decision_total
    emit_progress(force=True)

    pnls = [t["pnl"] for t in trades]
    winners = [x for x in pnls if x > 0]
    losers = [x for x in pnls if x < 0]
    gross_profit = sum(winners)
    gross_loss = abs(sum(losers))
    total = len(trades)
    by_setup = defaultdict(list)
    for t in trades:
        by_setup[t["setup"]].append(t["pnl"])
    setup_stats = {}
    for name, vals in by_setup.items():
        setup_stats[name] = {
            "occurrences": len(vals), "wins": sum(v > 0 for v in vals), "losses": sum(v < 0 for v in vals),
            "net_pnl": round(sum(vals), 2), "expectancy": round(sum(vals) / len(vals), 2),
            "win_rate_pct": round(sum(v > 0 for v in vals) / len(vals) * 100, 2),
        }
    return {
        "valid": True, "config": asdict(cfg), "data_source": "historical_option_bars", "data_format": "phase9a_fixed_contracts",
        "metrics": {
            "initial_capital": cfg.initial_capital, "ending_capital": round(capital, 2),
            "net_pnl": round(capital - cfg.initial_capital, 2), "total_trades": total,
            "wins": len(winners), "losses": len(losers),
            "win_rate_pct": round(len(winners) / total * 100, 2) if total else 0.0,
            "expectancy_per_trade": round(sum(pnls) / total, 2) if total else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else (None if gross_profit else 0.0),
            "max_drawdown_pct": round(max_dd, 2),
            "avg_r": round(sum(t["r_multiple"] for t in trades) / total, 2) if total else 0.0,
            "target_exits": sum(t["exit_reason"] == "TARGET" for t in trades),
            "stop_exits": sum(t["exit_reason"] == "STOP" for t in trades),
            "time_exits": sum(t["exit_reason"] == "TIME_EXIT" for t in trades),
            "skipped_setup_counts": dict(skipped), "setup_stats": setup_stats,
        },
        "trades": trades,
        "data_note": "Research-only fixed-contract backtest. Dhan rolling historical data may contain derived expiry/Delta and may lack bid/ask; results require independent validation and out-of-sample/walk-forward testing before any real-money use.",
    }
