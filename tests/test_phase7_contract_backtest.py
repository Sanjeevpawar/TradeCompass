from datetime import datetime, timedelta

from backtesting.v2.models import HistoricalOptionBar
from backtesting.v2.option_selector import select_historical_option
from backtesting.v2.engine import ContractBacktestConfig, run_contract_backtest
from data.candle_models import Candle


def make_candles(n=100):
    start = datetime(2026, 1, 1, 9, 15)
    price = 100.0
    out = []
    for i in range(n):
        op = price
        close = price + 1.2
        out.append(Candle((start + timedelta(minutes=5*i)).isoformat(), op, close + 0.5, op - 0.2, close, 2000))
        price = close
    return out


def make_options(candles):
    expiry = "2026-01-10"
    out = []
    for idx, c in enumerate(candles):
        premium = 25 + idx * 0.8
        out.append(HistoricalOptionBar(
            timestamp=c.timestamp, expiry=expiry, strike=130.0, option_type="CE",
            open=premium, high=premium + 1.0, low=max(0.05, premium - 0.5), close=premium + 0.4,
            volume=10000, iv=15.0, delta=0.55, theta=-0.08, gamma=0.01, vega=0.1,
            bid=premium - 0.1, ask=premium + 0.1, spot=c.close,
        ))
    return out


def test_historical_option_selector_prefers_delta_near_target():
    ts = "2026-01-02T10:00:00"
    bars = [
        HistoricalOptionBar(ts, "2026-01-15", 130, "CE", 100, 101, 99, 100, 1000, delta=.46, bid=99.9, ask=100.1),
        HistoricalOptionBar(ts, "2026-01-15", 131, "CE", 100, 101, 99, 100, 1000, delta=.55, bid=99.9, ask=100.1),
        HistoricalOptionBar(ts, "2026-01-15", 132, "CE", 100, 101, 99, 100, 1000, delta=.64, bid=99.9, ask=100.1),
    ]
    result = select_historical_option(bars, ts, "CALL", selection_timestamp=ts)
    assert result["selected"]["strike"] == 131
    assert result["selected"]["delta"] == .55


def test_contract_backtester_uses_real_option_bars():
    candles = make_candles()
    options = make_options(candles)
    result = run_contract_backtest(candles, options, ContractBacktestConfig(
        initial_capital=100000, risk_per_trade_pct=10, lot_size=1, max_bars_in_trade=4
    ))
    assert result["valid"] is True
    assert result["data_source"] == "historical_option_bars"
    assert result["trades"]
    trade = result["trades"][0]
    assert trade["strike"] == 130.0
    assert trade["option_type"] == "CE"
    assert "selection_reason" in trade
    assert "setup_stats" in result["metrics"]


def test_contract_backtester_enters_at_option_open_not_close():
    candles = make_candles()
    options = make_options(candles)
    result = run_contract_backtest(candles, options, ContractBacktestConfig(
        initial_capital=100000, risk_per_trade_pct=10, lot_size=1, max_bars_in_trade=4
    ))
    assert result["trades"]
    assert result["trades"][0]["entry_premium"] == 65.0
    assert result["trades"][0]["entry_reference"] == "historical_option_open"


def test_historical_option_selector_uses_pre_entry_completed_bar_for_selection():
    selection_ts = "2026-01-02T10:00:00"
    entry_ts = "2026-01-02T10:05:00"
    bars = [
        # Pre-entry evidence: strike 130 is closest to target delta.
        HistoricalOptionBar(selection_ts, "2026-01-15", 130, "CE", 100, 101, 99, 100, 1000, delta=.55, bid=99.9, ask=100.1),
        HistoricalOptionBar(selection_ts, "2026-01-15", 131, "CE", 100, 101, 99, 100, 5000, delta=.60, bid=99.9, ask=100.1),
        # At entry, strike 131 would look artificially attractive if current-bar
        # delta/volume were used for selection. That must not change the choice.
        HistoricalOptionBar(entry_ts, "2026-01-15", 130, "CE", 110, 111, 109, 110, 10, delta=.40, bid=109.9, ask=110.1),
        HistoricalOptionBar(entry_ts, "2026-01-15", 131, "CE", 90, 91, 89, 90, 999999, delta=.55, bid=89.9, ask=90.1),
    ]
    result = select_historical_option(
        bars, entry_ts, "CALL", selection_timestamp=selection_ts, max_premium=105
    )
    assert result["selected"]["strike"] == 130
    assert result["selected"]["premium"] == 110
    assert result["selected"]["delta"] == .55
    assert result["selected"]["selection_timestamp"] == selection_ts
