from __future__ import annotations

from data.dhan_historical import DhanHistoricalClient, DhanHistoricalConfig, rolling_option_records


def main() -> None:
    cfg = DhanHistoricalConfig.from_env()
    client = DhanHistoricalClient(cfg)

    profile = client.session.get(
        "https://api.dhan.co/v2/profile",
        timeout=cfg.timeout_seconds,
    )
    print("PROFILE HTTP:", profile.status_code)
    profile.raise_for_status()
    pdata = profile.json()
    print("Data plan:", pdata.get("dataPlan"))
    print("Token validity:", pdata.get("tokenValidity"))

    underlying = client.intraday_candles(
        security_id="13",
        interval=5,
        from_date="2026-09-14 09:15:00",
        to_date="2026-09-17 15:30:00",
    )
    print("NIFTY candle count:", len(underlying.get("timestamp", [])))

    options = client.rolling_expired_options(
        security_id="13",
        strike="ATM",
        option_type="CALL",
        expiry_flag="WEEK",
        expiry_code=cfg.default_expiry_code,
        interval=5,
        required_data=["open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot"],
        from_date="2026-09-01",
        to_date="2026-09-05",
    )
    rows = rolling_option_records(options, option_type="CALL")
    print("Option candle count:", len(rows))
    if rows:
        print("First option row:", rows[0])
        print("Last option row:", rows[-1])
        print("IV/OI/strike/spot present:", all(rows[0].get(k) is not None for k in ("iv", "oi", "strike", "spot")))


if __name__ == "__main__":
    main()
