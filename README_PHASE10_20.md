# Phase 10.20 — Option Chain Evidence Validation

Purpose:
- inspect the historical option-chain intelligence output;
- explicitly report incomplete snapshots;
- summarize distributions and coverage;
- preserve a research-only boundary.

This phase does NOT:
- add trading rules;
- classify PCR as bullish/bearish;
- label OI as definite writers;
- modify the strategy, option selector, risk engine, or backtester.

Commands:
    py -m pytest -q
    py -m scripts.validate_option_chain_evidence

Important:
The Phase 10.17 intelligence report is a compact aggregate report rather
than a full embedded list of 18,665 snapshot objects. Phase 10.20B therefore
uses its explicit snapshot-count metadata. It does not invent per-snapshot
coverage details that are not present in that report.
