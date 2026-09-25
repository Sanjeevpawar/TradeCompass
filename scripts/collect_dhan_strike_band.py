from __future__ import annotations

import argparse

from data.dhan_strike_band import StrikeBandConfig, collect_with_dhan


def parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def main() -> None:
    p = argparse.ArgumentParser(description="Collect Dhan rolling NIFTY options across an ATM-relative strike band.")
    p.add_argument("--from-date", required=True)
    p.add_argument("--to-date", required=True, help="End date is non-inclusive, matching Dhan API.")
    p.add_argument("--security-id", default="13")
    p.add_argument("--expiry-flag", choices=["WEEK", "MONTH"], default="WEEK")
    p.add_argument("--expiry-codes", default="1", help="Comma-separated Dhan expiry codes, e.g. 0,1")
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--offsets", default=",".join(str(i) for i in range(-10, 11)), help="Comma-separated offsets from ATM, -10..10")
    p.add_argument("--pause-seconds", type=float, default=0.5, help="Delay between requests; defaults to 0.5s to reduce rate-limit risk.")
    p.add_argument("--max-retries", type=int, default=5, help="Maximum retries for HTTP 429 responses.")
    p.add_argument("--retry-backoff-seconds", type=float, default=1.0, help="Initial exponential backoff for HTTP 429 responses.")
    p.add_argument("--output-call", default="data/dhan_samples/nifty_options_band_call.csv")
    p.add_argument("--output-put", default="data/dhan_samples/nifty_options_band_put.csv")
    p.add_argument("--report", default="data/dhan_samples/strike_band_collection_report.json")
    args = p.parse_args()

    config = StrikeBandConfig(
        security_id=args.security_id,
        expiry_flag=args.expiry_flag,
        expiry_codes=parse_ints(args.expiry_codes),
        interval=args.interval,
        offsets=parse_ints(args.offsets),
        pause_seconds=args.pause_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
    report = collect_with_dhan(
        start_date=args.from_date,
        end_date=args.to_date,
        config=config,
        output_call=args.output_call,
        output_put=args.output_put,
        report_path=args.report,
    )
    print(f"Strike-band collection: {report['status']}")
    print(f"Requests: {report['requests']['made']}")
    print(f"Request errors: {report['requests']['errors']}")
    print(f"Rows before deduplication: {report['rows']['before_deduplication']}")
    print(f"Rows after deduplication: {report['rows']['after_deduplication']}")
    print(f"CALL output: {args.output_call}")
    print(f"PUT output: {args.output_put}")
    print(f"Report: {args.report}")
    if report["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
