from pathlib import Path

from backtesting.v2.historical_adapter import load_reconstructed_option_bars
from backtesting.v2.option_selector import select_historical_option
from backtesting.v2.models import HistoricalOptionBar


def _row(ts, eligible="True", continuity="CONTINUOUS", strike="24000"):
    return f"{ts},2026-09-15,{strike},CE,100,105,95,101,10000,17.0,0.55,,,,,{continuity},DERIVED,{eligible}\n"


def test_adapter_accepts_phase9a_field_shape(tmp_path: Path):
    p = tmp_path / "fixed.csv"
    p.write_text(
        "timestamp,expiry,strike,option_type,open,high,low,close,volume,iv,model_delta,contract_continuity,contract_identity_status,reconstruction_eligible\n"
        "2026-09-01T09:15:00+05:30,2026-09-15,24000,CE,100,105,95,101,10000,17,0.55,CONTINUOUS,DERIVED,True\n",
        encoding="utf-8",
    )
    bars, report = load_reconstructed_option_bars(p)
    assert len(bars) == 1
    assert bars[0].delta == 0.55
    assert bars[0].open == 100
    assert report["identity"] == {"DERIVED": 1}


def test_adapter_filters_gapped_and_ineligible(tmp_path: Path):
    p = tmp_path / "fixed.csv"
    p.write_text(
        "timestamp,expiry,strike,option_type,open,high,low,close,volume,iv,model_delta,contract_continuity,contract_identity_status,reconstruction_eligible\n"
        "2026-09-01T09:15:00+05:30,2026-09-15,24000,CE,100,105,95,101,10000,17,0.55,GAPPED,DERIVED,False\n",
        encoding="utf-8",
    )
    bars, report = load_reconstructed_option_bars(p)
    assert bars == []
    assert report["output"]["rejected"]["not_reconstruction_eligible"] == 1


def test_selector_uses_pre_entry_close_for_premium_limit_and_entry_open_for_fill():
    selection_ts = "2026-09-01T09:10:00+05:30"
    entry_ts = "2026-09-01T09:15:00+05:30"
    selection_bar = HistoricalOptionBar(
        selection_ts, "2026-09-15", 24000, "CE",
        100, 130, 95, 100, 10000, iv=17, delta=.55
    )
    entry_bar = HistoricalOptionBar(
        entry_ts, "2026-09-15", 24000, "CE",
        110, 130, 105, 125, 10000, iv=17, delta=.40
    )
    result = select_historical_option(
        [selection_bar, entry_bar], entry_ts, "CALL",
        selection_timestamp=selection_ts, max_premium=105, require_spread_data=False
    )
    assert result["selected"] is not None
    assert result["selected"]["premium"] == 110
    assert result["selected"]["delta"] == .55


def test_selector_can_explicitly_require_spread_data():
    bar = HistoricalOptionBar(
        "2026-09-01T09:15:00+05:30", "2026-09-15", 24000, "CE",
        100, 105, 95, 101, 10000, iv=17, delta=.55
    )
    result = select_historical_option(
        [bar], bar.timestamp, "CALL", selection_timestamp=bar.timestamp, require_spread_data=True
    )
    assert result["selected"] is None
    assert result["rejected"]["spread data unavailable"] == 1
