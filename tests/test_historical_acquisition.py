from __future__ import annotations

import json
from pathlib import Path

from data.historical_acquisition import AcquisitionConfig, ninety_day_chunks, acquire_history


class FakeClient:
    def __init__(self):
        self.underlying_calls = []
        self.option_calls = []

    def intraday_candles(self, **kwargs):
        self.underlying_calls.append(kwargs)
        return {"data": {"timestamp": [1, 2], "open": [100, 101], "high": [102, 103], "low": [99, 100], "close": [101, 102], "volume": [10, 20]}}

    def rolling_expired_options(self, **kwargs):
        self.option_calls.append(kwargs)
        # Minimal valid Dhan-shaped response.
        return {"data": {"ce": {"timestamp": [1], "open": [10], "high": [11], "low": [9], "close": [10.5], "iv": [15], "volume": [100], "strike": [24000], "oi": [1000], "spot": [24010]}, "pe": {"timestamp": [1], "open": [10], "high": [11], "low": [9], "close": [10.5], "iv": [15], "volume": [100], "strike": [24000], "oi": [1000], "spot": [24010]}}}


def test_ninety_day_chunks_respects_api_limit():
    chunks = ninety_day_chunks("2025-01-01", "2025-07-01")
    assert chunks == [("2025-01-01", "2025-04-01"), ("2025-04-01", "2025-06-30"), ("2025-06-30", "2025-07-01")]


def test_config_validation():
    cfg = AcquisitionConfig(start_date="2026-01-01", end_date="2026-02-01")
    cfg.validate()


def test_acquisition_writes_manifest_and_chunks(tmp_path: Path):
    client = FakeClient()
    cfg = AcquisitionConfig(start_date="2026-01-01", end_date="2026-01-02", offsets=(0,), output_root=str(tmp_path / "raw"), pause_seconds=0)
    result = acquire_history(client, cfg)
    assert result["status"] == "PASS"
    assert result["chunks"]["total"] == 2
    manifest = json.loads((tmp_path / "raw" / "acquisition_manifest.json").read_text())
    assert len(manifest["chunks"]) == 2
    assert len(client.underlying_calls) == 1
    assert len(client.option_calls) == 2


def test_acquisition_is_resumable(tmp_path: Path):
    client = FakeClient()
    cfg = AcquisitionConfig(start_date="2026-01-01", end_date="2026-01-02", offsets=(0,), output_root=str(tmp_path / "raw"), pause_seconds=0)
    assert acquire_history(client, cfg)["status"] == "PASS"
    client2 = FakeClient()
    assert acquire_history(client2, cfg)["status"] == "PASS"
    assert client2.underlying_calls == []
    assert client2.option_calls == []
