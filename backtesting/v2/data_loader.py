from __future__ import annotations

import csv
from pathlib import Path
from backtesting.v2.models import HistoricalOptionBar
from data.candle_models import Candle


def load_option_bars_csv(path: str | Path) -> list[HistoricalOptionBar]:
    """Load historical option bars.

    Required columns: timestamp, expiry, strike, option_type, open, high, low, close.
    Optional: volume, iv, delta, theta, gamma, vega, bid, ask, spot.
    """
    rows: list[HistoricalOptionBar] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"timestamp", "expiry", "strike", "option_type", "open", "high", "low", "close"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required option CSV columns: {sorted(missing)}")
        for r in reader:
            rows.append(HistoricalOptionBar(
                timestamp=r["timestamp"], expiry=r["expiry"], strike=float(r["strike"]),
                option_type=r["option_type"].upper(), open=float(r["open"]), high=float(r["high"]),
                low=float(r["low"]), close=float(r["close"]), volume=int(float(r.get("volume", 0) or 0)),
                iv=float(r["iv"]) if r.get("iv") else None,
                delta=float(r["delta"]) if r.get("delta") else None,
                theta=float(r["theta"]) if r.get("theta") else None,
                gamma=float(r["gamma"]) if r.get("gamma") else None,
                vega=float(r["vega"]) if r.get("vega") else None,
                bid=float(r["bid"]) if r.get("bid") else None,
                ask=float(r["ask"]) if r.get("ask") else None,
                spot=float(r["spot"]) if r.get("spot") else None,
            ))
    return sorted(rows, key=lambda x: x.timestamp)


def load_underlying_csv(path: str | Path) -> list[Candle]:
    from backtesting.v1.data_loader import load_candles_csv
    return load_candles_csv(path)
