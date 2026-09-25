# Phase 10.20D — Option Chain Evidence Validation Fix

The Phase 10.17 report stores the full historical snapshot records under
`snapshots_data`. The previous validator incorrectly looked only at
`snapshots`, which is the integer count.

This fix reads `snapshots_data` and therefore can inspect the five actual
coverage-incomplete timestamps and calculate the real distributions.

No trading logic is changed.

Run:
    py -m pytest -q
    py -m scripts.validate_option_chain_evidence
