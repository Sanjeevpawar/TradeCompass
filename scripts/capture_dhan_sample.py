from __future__ import annotations

import argparse

from data.dhan_historical import DhanHistoricalConfig, DhanHistoricalClient
from data.dhan_sample_pipeline import capture_sample


def main() -> None:
    p = argparse.ArgumentParser(description="Capture a small, normalized Dhan historical NIFTY sample.")
    p.add_argument("--from-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--to-date", required=True, help="YYYY-MM-DD (non-inclusive)")
    p.add_argument("--interval", type=int, default=5, choices=[1, 5, 15, 25, 60])
    p.add_argument("--expiry-flag", default="WEEK", choices=["WEEK", "MONTH"])
    p.add_argument("--expiry-code", type=int, default=1, choices=[0, 1, 2])
    p.add_argument("--strike", default="ATM")
    p.add_argument("--out-dir", default="data/dhan_samples")
    args = p.parse_args()

    client = DhanHistoricalClient(DhanHistoricalConfig.from_env())
    result = capture_sample(client, from_date=args.from_date, to_date=args.to_date,
                            out_dir=args.out_dir, interval=args.interval,
                            expiry_flag=args.expiry_flag, expiry_code=args.expiry_code,
                            strike_mode=args.strike)
    print("Capture complete")
    print(result)


if __name__ == "__main__":
    main()
