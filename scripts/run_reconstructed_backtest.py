from __future__ import annotations

import argparse
import json
from pathlib import Path

from backtesting.v2.reconstructed_runner import run_reconstructed_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Research-only backtest using Phase 9A fixed contracts.")
    parser.add_argument("--underlying", default="data/dhan_samples/nifty_underlying.csv")
    parser.add_argument("--options", default="data/dhan_samples/nifty_fixed_contracts.csv")
    parser.add_argument("--report", default="data/dhan_samples/phase9b_backtest_report.json")
    parser.add_argument(
        "--allow-missing-spread-data",
        action="store_true",
        help="Research-only: allow Dhan historical rows without bid/ask. Never fabricates spread.",
    )
    args = parser.parse_args()

    result = run_reconstructed_backtest(
        args.underlying, args.options,
        allow_missing_spread_data=args.allow_missing_spread_data,
    )
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print("Phase 9B reconstructed backtest: PASS" if result.get("valid") else "Phase 9B reconstructed backtest: INVALID")
    if result.get("valid"):
        print(f"Trades: {result['metrics']['total_trades']}")
        print(f"Net P&L: {result['metrics']['net_pnl']}")
        print(f"Win rate: {result['metrics']['win_rate_pct']}%")
        print(f"Skipped: {result['metrics']['skipped_setup_counts']}")
    else:
        print(f"Reason: {result.get('reason')}")
    print(f"Report: {report}")
    print("Trading gate: BLOCKED (research-only; no live orders)")


if __name__ == "__main__":
    main()
