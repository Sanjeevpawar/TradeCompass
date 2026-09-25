from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Iterable

from backtesting.v2.models import HistoricalOptionBar


def _date(text: str) -> date:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date()


def _spread_pct(bar: HistoricalOptionBar) -> float:
    if bar.bid is None or bar.ask is None or bar.open <= 0:
        return 999.0
    return max(bar.ask - bar.bid, 0.0) / bar.open * 100.0


def select_historical_option(
    bars: Iterable[HistoricalOptionBar],
    timestamp: str,
    direction: str,
    *,
    selection_timestamp: str,
    min_delta: float = 0.45,
    max_delta: float = 0.65,
    target_delta: float = 0.55,
    max_spread_pct: float = 2.0,
    require_spread_data: bool = True,
    max_premium: float = 500.0,
    min_volume: int = 1,
    max_dte: int = 14,
    min_dte: int = 1,
) -> dict:
    """Select a historical option without using future information.

    ``timestamp`` is the simulated entry timestamp. The entry price comes from
    that bar's OPEN. Contract-selection filters (delta, volume, spread and
    other bar-derived fields) are taken from ``selection_timestamp``. The
    backtester should pass the immediately preceding completed option bar so
    those fields were known before the simulated entry.

    ``selection_timestamp`` is required so callers cannot accidentally select
    a contract using information from the entry bar itself.
    """
    option_type = "CE" if direction == "CALL" else "PE"
    entry_date = _date(timestamp)
    candidates = []
    rejected = defaultdict(int)
    bars_list = bars if isinstance(bars, list) else list(bars)

    # Build the entry-bar lookup separately. Entry OPEN is allowed; all other
    # selection evidence comes from the completed pre-entry reference bar.
    entry_bars = {
        (b.expiry, b.strike, b.option_type): b
        for b in bars_list
        if b.timestamp == timestamp and b.option_type == option_type
    }

    for b in bars_list:
        if b.timestamp != selection_timestamp or b.option_type != option_type:
            continue
        entry_bar = entry_bars.get((b.expiry, b.strike, b.option_type))
        if entry_bar is None:
            rejected["missing entry bar"] += 1
            continue
        if entry_bar.open <= 0:
            rejected["non-positive entry premium"] += 1
            continue
        if b.delta is None or not (min_delta <= abs(b.delta) <= max_delta):
            rejected["delta outside range"] += 1
            continue
        # The premium constraint must use the completed pre-entry bar, not
        # the future entry OPEN. The entry OPEN is only the simulated fill
        # price after the contract has already been selected.
        if b.close > max_premium:
            rejected["premium above maximum"] += 1
            continue
        if b.volume < min_volume:
            rejected["insufficient selection-time volume"] += 1
            continue
        spread_available = b.bid is not None and b.ask is not None
        if require_spread_data and not spread_available:
            rejected["spread data unavailable"] += 1
            continue
        spread = _spread_pct(b) if spread_available else 0.0
        if spread_available and spread > max_spread_pct:
            rejected["wide bid/ask spread"] += 1
            continue
        try:
            dte = (_date(b.expiry) - entry_date).days
        except Exception:
            rejected["invalid expiry"] += 1
            continue
        if dte < min_dte or dte > max_dte:
            rejected["expiry outside DTE range"] += 1
            continue
        candidates.append((b, entry_bar, dte, spread, spread_available))

    if not candidates:
        return {
            "selected": None,
            "rejected": dict(rejected),
            "reason": "No historical option candidate passed the contract rules",
        }

    def rank(item):
        b, _entry_bar, dte, spread, _spread_available = item
        return (abs(abs(b.delta or 0) - target_delta), spread, -b.volume, dte)

    selected, entry_bar, dte, spread, spread_available = sorted(candidates, key=rank)[0]
    alternatives = []
    for b, entry_b, d, s, sa in sorted(candidates, key=rank)[1:4]:
        alternatives.append({
            "strike": b.strike,
            "option_type": b.option_type,
            "premium": entry_b.open,
            "delta": b.delta,
            "iv": b.iv,
            "volume": b.volume,
            "spread_pct": round(s, 3),
            "spread_data_status": "AVAILABLE" if sa else "UNAVAILABLE",
            "expiry": b.expiry,
            "dte": d,
            "reason_not_selected": "Ranked below the selected contract on pre-entry delta, spread, liquidity and expiry fit",
        })
    return {
        "selected": {
            "timestamp": entry_bar.timestamp,
            "selection_timestamp": selected.timestamp,
            "expiry": selected.expiry,
            "strike": selected.strike,
            "option_type": selected.option_type,
            "premium": entry_bar.open,
            "delta": selected.delta,
            "iv": selected.iv,
            "theta": selected.theta,
            "gamma": selected.gamma,
            "vega": selected.vega,
            "volume": selected.volume,
            "bid": selected.bid,
            "ask": selected.ask,
            "spread_pct": round(spread, 3),
            "spread_data_status": "AVAILABLE" if spread_available else "UNAVAILABLE",
            "dte": dte,
        },
        "alternatives": alternatives,
        "rejected": dict(rejected),
        "reason": "Selected contract uses the pre-entry completed bar for Delta/liquidity/spread and the entry bar OPEN for execution price",
    }
