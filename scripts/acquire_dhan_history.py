from __future__ import annotations

import argparse
from datetime import date

from data.dhan_historical import DhanHistoricalClient, DhanHistoricalConfig
from data.historical_acquisition import AcquisitionConfig, acquire_history


def ints(value: str) -> tuple[int, ...]:
    return tuple(int(x.strip()) for x in value.split(",") if x.strip())


def main() -> None:
    p = argparse.ArgumentParser(description="Resumable Dhan NIFTY historical acquisition for TradeCompass research.")
    p.add_argument("--from-date", required=True)
    p.add_argument("--to-date", required=True, help="End date is non-inclusive.")
    p.add_argument("--security-id", default="13")
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--expiry-flag", choices=["WEEK", "MONTH"], default="WEEK")
    p.add_argument("--expiry-codes", default="1")
    p.add_argument("--offsets", default=",".join(str(i) for i in range(-10, 11)))
    p.add_argument("--output-root", default="data/dhan_history/raw")
    p.add_argument("--pause-seconds", type=float, default=0.5)
    p.add_argument("--max-retries", type=int, default=5)
    p.add_argument("--retry-backoff-seconds", type=float, default=1.0)
    args = p.parse_args()

    config = AcquisitionConfig(
        security_id=args.security_id,
        start_date=args.from_date,
        end_date=args.to_date,
        interval=args.interval,
        expiry_flag=args.expiry_flag,
        expiry_codes=ints(args.expiry_codes),
        offsets=ints(args.offsets),
        output_root=args.output_root,
        pause_seconds=args.pause_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
    client = DhanHistoricalClient(DhanHistoricalConfig.from_env())
    result = acquire_history(client, config)
    print(f"Historical acquisition: {result['status']}")
    print(f"Chunks: {result['chunks']['passed']}/{result['chunks']['total']} passed")
    print(f"Underlying chunks expected: {result['underlying_chunks_expected']}")
    print(f"Option chunks expected: {result['option_chunks_expected']}")
    print(f"Manifest: {result['manifest']}")
    if result["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
