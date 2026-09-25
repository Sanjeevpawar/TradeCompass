from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path

from backtesting.v2.reconstructed_runner import run_reconstructed_backtest

DEFAULT_UNDERLYING = "data/dhan_history/reconstructed/nifty_underlying_1y.csv"
DEFAULT_OPTIONS = "data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv"
DEFAULT_REPORT = "data/dhan_history/reconstructed/full_year_backtest_report.json"


def _format_elapsed(seconds: float) -> str:
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only baseline backtest using the Phase 10 full-year fixed-contract dataset."
    )
    parser.add_argument("--underlying", default=DEFAULT_UNDERLYING)
    parser.add_argument("--options", default=DEFAULT_OPTIONS)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument(
        "--allow-missing-spread-data",
        action="store_true",
        help="Research-only: allow historical rows without bid/ask. Never fabricates spread.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Update progress after this many decision-loop iterations. Default: 100.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=int,
        default=15,
        help="Print a heartbeat at this interval even during a slow iteration. Default: 15 seconds.",
    )
    args = parser.parse_args()

    if args.progress_every < 1:
        parser.error("--progress-every must be >= 1")
    if args.heartbeat_seconds < 1:
        parser.error("--heartbeat-seconds must be >= 1")

    print("Phase 10 full-year baseline backtest", flush=True)
    print(f"Underlying: {args.underlying}", flush=True)
    print(f"Options:    {args.options}", flush=True)
    print(f"Report:     {args.report}", flush=True)
    print(f"Progress:   every {args.progress_every} decision-loop iterations", flush=True)
    print("Mode:       research-only; no live orders", flush=True)
    print("Starting backtest...", flush=True)

    started = time.monotonic()
    last_progress = {
        "processed": 0,
        "total": 0,
        "percent": 0.0,
        "current_timestamp": None,
        "signals": 0,
        "trades": 0,
        "skipped": {},
    }
    lock = threading.Lock()
    stop_event = threading.Event()

    def on_progress(info: dict) -> None:
        with lock:
            last_progress.update(info)
            snapshot = dict(last_progress)
        elapsed = _format_elapsed(time.monotonic() - started)
        print(
            f"[PROGRESS] {snapshot['percent']:6.2f}% | "
            f"decision candles {snapshot['processed']}/{snapshot['total']} | "
            f"signals {snapshot['signals']} | trades {snapshot['trades']} | "
            f"current {snapshot['current_timestamp']} | elapsed {elapsed}",
            flush=True,
        )

    def heartbeat() -> None:
        while not stop_event.wait(args.heartbeat_seconds):
            with lock:
                snapshot = dict(last_progress)
            elapsed = _format_elapsed(time.monotonic() - started)
            print(
                f"[RUNNING] {snapshot['percent']:6.2f}% | "
                f"decision candles {snapshot['processed']}/{snapshot['total']} | "
                f"signals {snapshot['signals']} | trades {snapshot['trades']} | "
                f"last checkpoint {snapshot['current_timestamp']} | elapsed {elapsed}",
                flush=True,
            )

    heartbeat_thread = threading.Thread(target=heartbeat, name="backtest-heartbeat", daemon=True)
    heartbeat_thread.start()

    try:
        result = run_reconstructed_backtest(
            args.underlying,
            args.options,
            allow_missing_spread_data=args.allow_missing_spread_data,
            progress_callback=on_progress,
            progress_interval=args.progress_every,
        )
    except KeyboardInterrupt:
        print("\nBacktest interrupted by user.", flush=True)
        raise
    finally:
        stop_event.set()

    elapsed = _format_elapsed(time.monotonic() - started)
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"Backtest finished in {elapsed}", flush=True)
    print(
        "Phase 10 full-year baseline backtest: PASS"
        if result.get("valid")
        else "Phase 10 full-year baseline backtest: INVALID",
        flush=True,
    )
    if result.get("valid"):
        metrics = result["metrics"]
        print(f"Trades: {metrics['total_trades']}", flush=True)
        print(f"Net P&L: {metrics['net_pnl']}", flush=True)
        print(f"Win rate: {metrics['win_rate_pct']}%", flush=True)
        print(f"Skipped: {metrics['skipped_setup_counts']}", flush=True)
    else:
        print(f"Reason: {result.get('reason')}", flush=True)
    print(f"Report: {report}", flush=True)
    print("Trading gate: BLOCKED (research-only; no live orders)", flush=True)


if __name__ == "__main__":
    main()
