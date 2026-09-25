from datetime import datetime, timedelta

from backtesting.v1.engine import BacktestConfig, run_backtest
from data.candle_models import Candle


def make_trend_candles(n=90):
    out=[]
    start=datetime(2026,1,1,9,15)
    price=100.0
    for i in range(n):
        op=price
        close=price+1.2
        high=close+0.5
        low=op-0.2
        out.append(Candle((start+timedelta(minutes=5*i)).isoformat(),op,high,low,close,1000+i*10))
        price=close
    return out


def test_backtester_runs_and_reports_metrics():
    result=run_backtest(make_trend_candles(), BacktestConfig(initial_capital=100000, max_bars_in_trade=6))
    assert result["valid"] is True
    assert "max_drawdown_pct" in result["metrics"]
    assert isinstance(result["trades"], list)
    assert "synthetic option-premium proxy" in result["data_note"]
