# Phase 10.22 — Chain Evidence vs Historical NIFTY Setups

Purpose:
Join the existing deterministic NIFTY option-buying setup signals with the
option-chain snapshot at the exact same completed-candle timestamp.

The phase also records forward NIFTY price behaviour (1/3/6/12 candles) as
an outcome field. Forward data is never used to generate the signal.

This is research only. It does NOT:
- create PCR/OI thresholds;
- modify setup detection;
- modify option selection;
- modify risk;
- modify the backtester;
- enable live trading.

Run:
    py -m pytest -q
    py -m scripts.analyze_chain_vs_setups
