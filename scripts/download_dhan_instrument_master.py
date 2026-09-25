from __future__ import annotations

import argparse
from pathlib import Path
import requests

COMPACT_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
DETAILED_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Dhan instrument master.")
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Download the detailed instrument master (recommended for Phase 8.5).",
    )
    parser.add_argument(
        "--output",
        default="data/dhan_samples/dhan_instrument_master_detailed.csv",
    )
    args = parser.parse_args()

    url = DETAILED_URL if args.detailed else COMPACT_URL
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(response.content)

    print(f"Downloaded instrument master: {out}")
    print(f"Source: {url}")
    print(f"Bytes: {len(response.content)}")


if __name__ == "__main__":
    main()
