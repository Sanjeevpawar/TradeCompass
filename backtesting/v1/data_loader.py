from __future__ import annotations

import csv
from pathlib import Path
from data.candle_models import Candle


def load_candles_csv(path: str | Path) -> list[Candle]:
    """Load OHLCV candles from CSV with columns timestamp,open,high,low,close,volume."""
    rows: list[Candle] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"timestamp", "open", "high", "low", "close"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required CSV columns: {sorted(missing)}")
        for r in reader:
            rows.append(Candle(
                timestamp=r["timestamp"],
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=int(float(r.get("volume", 0) or 0)),
                oi=int(float(r["oi"])) if r.get("oi") else None,
            ))
    return rows
