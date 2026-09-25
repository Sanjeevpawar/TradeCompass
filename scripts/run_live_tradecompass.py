from __future__ import annotations

import argparse
import json
import os
import time

from live.engine import LiveTradeCompassEngine


def main():
    parser = argparse.ArgumentParser(description="Read-only live TradeCompass signal monitor")
    parser.add_argument("--poll-seconds", type=int, default=int(os.getenv("TRADECOMPASS_LIVE_POLL_SECONDS", "30")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    engine = LiveTradeCompassEngine()
    while True:
        try:
            result = engine.snapshot()
            print(json.dumps(result["approaches"], indent=2, default=str))
            print(f"[LIVE] {result['timestamp_ist']} | NIFTY {result['market']['spot']} | execution={result['execution_enabled']}")
        except Exception as exc:
            print(f"[LIVE ERROR] {type(exc).__name__}: {exc}")
        if args.once:
            break
        time.sleep(max(5, args.poll_seconds))


if __name__ == "__main__":
    main()
