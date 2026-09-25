from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SignalStore:
    """Small persistent SQLite store for live signal observations."""

    def __init__(self, path: str = "data/live/tradecompass_live.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_key TEXT UNIQUE NOT NULL,
                    candle_timestamp TEXT NOT NULL,
                    approach TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    direction TEXT,
                    setup TEXT,
                    score REAL,
                    spot REAL,
                    option_json TEXT,
                    risk_json TEXT,
                    evidence_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(candle_timestamp)")

    def record(self, *, candle_timestamp: str, approach: str, result: dict):
        key = f"{candle_timestamp}|{approach}"
        with self._connect() as con:
            con.execute(
                """INSERT OR IGNORE INTO signals
                   (signal_key,candle_timestamp,approach,signal,direction,setup,score,spot,option_json,risk_json,evidence_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    key, candle_timestamp, approach,
                    result.get("signal", "WAIT"), result.get("direction"), result.get("setup"),
                    result.get("score", result.get("evidence_score")), result.get("spot"),
                    json.dumps(result.get("suggested_option"), default=str),
                    json.dumps(result.get("risk"), default=str),
                    json.dumps(result.get("evidence", result.get("reasons", [])), default=str),
                ),
            )

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
