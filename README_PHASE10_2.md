# Phase 10.2 — Raw Acquisition Validation Fix

Phase 10 acquisition intentionally uses inclusive calendar chunk boundaries. Adjacent chunks therefore overlap on the shared boundary date. The previous validator incorrectly treated these expected overlaps as errors.

This patch allows duplicates only when their timestamp falls on the intentional shared boundary date. Duplicate records outside that date remain errors. Raw data is not modified and no prices are forward-filled.

Run:
`py -m pytest -q tests/test_raw_acquisition_validation.py`
then:
`py -m scripts.validate_raw_acquisition`

A PASS means the raw chunks have no unexpected cross-chunk duplicates. It does not approve backtesting.
