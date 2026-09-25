# Phase 10.20C — Option Chain Evidence Validation Fix

Fixes Phase 10.20B handling of the actual Phase 10.17 compact report.

The source report may contain:
- `snapshots` as an integer count, not a list;
- `coverage_incomplete` as an aggregate count;
- aggregate medians.

The validator now:
- handles integer snapshot counts;
- preserves aggregate coverage counts;
- uses aggregate medians when present;
- supports embedded snapshot lists for tests/future reports;
- never invents missing per-snapshot details.

No strategy, option selection, risk, or backtest logic is changed.

Run:
    py -m pytest -q
    py -m scripts.validate_option_chain_evidence
