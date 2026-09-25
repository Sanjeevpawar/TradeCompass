# Phase 10.1 — Raw Acquisition Validation

Validates the completed Phase 10 raw Dhan acquisition before consolidation.
Because acquisition chunks share boundary dates, this phase checks adjacent chunk files
for duplicate timestamps (underlying) and duplicate timestamp+strike+option_type
(option data). It does not modify raw data and does not forward-fill.

Run:
`py -m pytest -q tests/test_raw_acquisition_validation.py`

Then:
`py -m scripts.validate_raw_acquisition`

A PASS means raw chunk boundaries are safe to consolidate. It does not approve
historical backtesting; fixed-contract reconstruction remains the next gate.
