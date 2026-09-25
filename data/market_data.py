

def get_daily_market_data():
    return {
        "close": 26042,
        "ema20": 25980,
        "ema50": 25890,
        "sma200": 25200,
        "high_20": 26200,
        "low_20": 25850,
        "volume_today": 1.0,
        "volume_avg_20": 1.0
    }


def get_spot_market_data():
    """
    SPOT price context (intraday snapshot)
    """
    return {
        "spot": 26042,
        "day_high": 26120,
        "day_low": 25980,
        "prev_close": 26010
    }


def get_option_chain_data():
    """
    Simplified option chain snapshot
    (Later this will come from NSE / broker API)
    """
    return {
        "pcr": 0.65,
        "max_pain": 26050,
        "call_oi_resistance": 26100,
        "put_oi_support": 25900,
        "iv_state": "normal"   # low / normal / high
    }

def get_live_market_snapshot():
    """
    Mock live market snapshot for monitoring
    """
    return {
        "spot": 26040,
        "pnl": 1200,        # current profit/loss
        "max_loss": 10000,
        "max_profit": 5000
    }


def get_option_ltp_snapshot():
    """
    Mock option LTPs for each strike
    """
    return {
        25900: 90,
        25600: 20,
        26100: 110,
        26400: 15
    }
