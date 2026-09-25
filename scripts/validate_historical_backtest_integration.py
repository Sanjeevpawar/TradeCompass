from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from backtesting.v2.historical_adapter import load_reconstructed_option_bars
from backtesting.v2.data_loader import load_underlying_csv

DEFAULT_UNDERLYING = "data/dhan_history/reconstructed/nifty_underlying_1y.csv"
DEFAULT_OPTIONS = "data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv"
DEFAULT_REPORT = Path('data/dhan_history/reconstructed/historical_backtest_integration_report.json')


def _raw_counts(path: Path) -> dict:
    rows = 0
    eligible = 0
    contracts = set()
    continuity = Counter()
    identity = Counter()
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows += 1
            if str(row.get('reconstruction_eligible') or '').strip().lower() == 'true':
                eligible += 1
            key = row.get('contract_key')
            if key:
                contracts.add(key)
            continuity[str(row.get('contract_continuity') or '').upper()] += 1
            identity[str(row.get('contract_identity_status') or row.get('identity_status') or 'UNKNOWN').upper()] += 1
    return {
        'rows': rows,
        'eligible_rows': eligible,
        'contracts': len(contracts),
        'continuity': dict(continuity),
        'identity': dict(identity),
    }


def validate(underlying_path: Path = DEFAULT_UNDERLYING, options_path: Path = DEFAULT_OPTIONS) -> dict:
    if not underlying_path.exists():
        raise FileNotFoundError(f'Underlying dataset not found: {underlying_path}')
    if not options_path.exists():
        raise FileNotFoundError(f'Fixed-contract dataset not found: {options_path}')

    raw = _raw_counts(options_path)
    candles = load_underlying_csv(underlying_path)
    bars, adapter_report = load_reconstructed_option_bars(options_path)

    timestamps = {c.timestamp for c in candles}
    option_timestamps = {b.timestamp for b in bars}
    overlap = timestamps & option_timestamps

    # Confirm the adapter is feeding only the eligible continuous contracts.
    adapter_bars = len(bars)
    expected_eligible_rows = raw['eligible_rows']
    checks = {
        'underlying_loaded': len(candles) > 0,
        'options_loaded': adapter_bars > 0,
        'eligible_rows_match_adapter': adapter_bars == expected_eligible_rows,
        'underlying_option_timestamp_overlap': len(overlap) > 0,
        'no_non_continuous_bars_loaded': adapter_report['output']['rejected'].get('not_continuous', 0) == 0,
        'derived_identity_preserved': adapter_report['identity'].get('DERIVED', 0) == adapter_bars,
    }

    valid = all(checks.values())
    result = {
        'valid': valid,
        'status': 'PASS' if valid else 'INVALID',
        'inputs': {
            'underlying': str(underlying_path),
            'options': str(options_path),
        },
        'dataset': {
            'underlying_rows': len(candles),
            'option_rows_raw': raw['rows'],
            'option_rows_eligible': expected_eligible_rows,
            'option_bars_loaded': adapter_bars,
            'contracts': raw['contracts'],
            'continuity': raw['continuity'],
            'identity': raw['identity'],
        },
        'adapter': adapter_report,
        'alignment': {
            'underlying_timestamps': len(timestamps),
            'option_timestamps': len(option_timestamps),
            'overlapping_timestamps': len(overlap),
        },
        'checks': checks,
        'policy': {
            'integration_only': True,
            'no_strategy_execution': True,
            'no_synthetic_option_prices': True,
            'continuous_contract_only': True,
            'full_year_dataset': True,
            'derived_identity_not_upgraded': True,
            'live_orders': False,
        },
    }
    return result


def main() -> None:
    result = validate()
    DEFAULT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    print(f"Historical backtest integration: {result['status']}")
    print(f"Underlying rows loaded: {result['dataset']['underlying_rows']}")
    print(f"Eligible option rows: {result['dataset']['option_rows_eligible']}")
    print(f"Option bars loaded by adapter: {result['dataset']['option_bars_loaded']}")
    print(f"Contracts: {result['dataset']['contracts']}")
    print(f"Overlapping timestamps: {result['alignment']['overlapping_timestamps']}")
    print(f"Checks passed: {sum(result['checks'].values())}/{len(result['checks'])}")
    print(f"Report: {DEFAULT_REPORT}")
    print("Trading gate: BLOCKED (integration-only; no strategy execution; no live orders)")
    if not result['valid']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
