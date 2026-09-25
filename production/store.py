from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class ProductionSignalStore:
    """Immutable decision snapshots plus append-only signal events."""

    def __init__(self, path: str = "data/live/tradecompass_phase12.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self):
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    direction TEXT,
                    setup TEXT,
                    strength TEXT,
                    spot REAL,
                    suggested_option_json TEXT,
                    risk_json TEXT NOT NULL,
                    technical_evidence_json TEXT NOT NULL,
                    chain_evidence_json TEXT NOT NULL,
                    reasons_json TEXT NOT NULL,
                    wait_reason TEXT,
                    engine_version TEXT NOT NULL,
                    config_version TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS signal_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_timestamp TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def record_signal(self, result: dict) -> None:
        with self._connect() as con:
            con.execute(
                """INSERT OR IGNORE INTO signals
                (signal_id,timestamp,symbol,decision,direction,setup,strength,spot,
                 suggested_option_json,risk_json,technical_evidence_json,chain_evidence_json,
                 reasons_json,wait_reason,engine_version,config_version)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result["signal_id"], result.get("timestamp"), result.get("symbol", "NIFTY"),
                    result.get("decision", "WAIT"), result.get("direction"), result.get("setup"),
                    result.get("strength"), result.get("spot"), json.dumps(result.get("suggested_option"), default=str),
                    json.dumps(result.get("risk", {}), default=str), json.dumps(result.get("technical_evidence", {}), default=str),
                    json.dumps(result.get("chain_evidence", {}), default=str), json.dumps(result.get("reasons", []), default=str),
                    result.get("wait_reason"), result.get("engine_version", "phase12-v1"), result.get("config_version", "phase12-v1"),
                ),
            )

    def record_event(self, signal_id: str, event_type: str, event_timestamp: str, payload: dict) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO signal_events(signal_id,event_type,event_timestamp,payload_json) VALUES (?,?,?,?)",
                (signal_id, event_type, event_timestamp, json.dumps(payload, default=str)),
            )

    def recent(self, limit: int = 50) -> list[dict]:
        with self._connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]
