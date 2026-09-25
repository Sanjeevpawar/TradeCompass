from __future__ import annotations

import argparse
from pathlib import Path

from data.contract_identity import enrich_csv


def main() -> None:
    p = argparse.ArgumentParser(description="Derive historical contract expiry and model delta for a Dhan rolling sample.")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    count = enrich_csv(args.input, args.output)
    print(f"Enrichment complete: {count} rows")
    print("NOTE: expiry and delta are derived research fields; they are not broker-reported contract identity/Greeks.")


if __name__ == "__main__":
    main()
