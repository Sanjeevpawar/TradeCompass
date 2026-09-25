# Phase 10.21 — Chain vs Setup Context Preparation

This phase prepares the historical option-chain evidence for comparison with
the existing NIFTY setup timestamps.

It remains descriptive:
- preserves same-time chain evidence;
- summarizes PCR/OI/Delta-OI distributions;
- preserves incomplete snapshots;
- does not create BUY/PUT rules;
- does not modify strategy, option selection, risk, or backtesting.

Run:
    py -m pytest -q
    py -m scripts.analyze_chain_setup_context
