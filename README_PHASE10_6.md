# TradeCompass Phase 10.6 — Reconstructed Dataset Validation

Adds a read-only validator for the Phase 10.5 reconstructed one-year dataset.

It checks required columns, timestamp parsing, fixed contract-key consistency,
contract-level duplicate timestamps, continuity/eligibility consistency,
DERIVED identity status, singleton consistency, and underlying timestamp uniqueness.

Run:

```powershell
py -m scripts.validate_reconstructed_dataset
```

The validator writes:
`data/dhan_history/reconstructed/reconstructed_dataset_validation_report.json`

A PASS validates dataset integrity only. It does not prove strategy profitability
and does not unlock live trading or automatically unlock production backtesting.
