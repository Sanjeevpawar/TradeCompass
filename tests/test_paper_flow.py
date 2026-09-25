from execution.paper_ledger import clear_trades, get_all_trades
from execution.paper_trade_engine import open_paper_trade
from core.pnl_engine import calculate_pnl


def setup_function():
    clear_trades()


def test_open_paper_trade_is_recorded():
    decision = {
        "strategy": "TEST",
        "action": "TRADE",
        "status": "ACTIVE",
        "max_profit": 5000,
        "max_loss": 10000,
        "legs": [
            {"strike": 26000, "instrument": "CALL", "side": "BUY", "entry_premium": 100}
        ],
    }
    open_paper_trade(decision)

    trades = get_all_trades()
    assert len(trades) == 1
    assert decision["trade_id"] == 1
    assert trades[0]["status"] == "OPEN"
    assert trades[0]["legs"][0]["entry_price"] == 100


def test_pnl_accepts_instrument_strike_keys():
    decision = {
        "legs": [
            {"strike": 26000, "instrument": "CALL", "side": "BUY", "entry_premium": 100}
        ]
    }
    result = calculate_pnl(decision, {"CALL_26000": 120})
    assert result["total_pnl"] == 1000


def test_missing_option_price_is_not_counted_as_zero():
    decision = {
        "legs": [
            {"strike": 26000, "instrument": "CALL", "side": "BUY", "entry_premium": 100}
        ]
    }
    result = calculate_pnl(decision, {})
    assert result["total_pnl"] == 0
    assert result["legs"] == []
