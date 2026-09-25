# TradeCompass Phase 10.18 — Option-Chain Intelligence Descriptive Analysis

## Purpose
Analyse the one-year historical option-chain intelligence output before defining any trading interpretation rules.

This phase is deliberately **descriptive only**. It does not modify BUY CALL / BUY PUT / WAIT, option selection, risk management, or backtesting.

## It reports
- PCR distribution
- Call/Put OI concentration statistics
- Distance of major OI peaks from spot
- ΔOI distribution and positive/negative proportions
- ATM IV/OI statistics
- Coverage and identity status
- Basic extreme-value warnings

## Run tests
```powershell
py -m pytest -q
```

## Run analysis
```powershell
py -m scripts.analyze_option_chain_intelligence
```

The command prints progress every 1,000 snapshots by default.

Input:
`data/dhan_history/reconstructed/option_chain_intelligence_1y.json`

Output:
`data/dhan_history/reconstructed/option_chain_intelligence_analysis_1y.json`

## Research discipline
- No trading signal is generated.
- No thresholds are optimized for P&L.
- No historical rows are removed because of their outcome.
- No future data is used.
- Large OI is not treated as proof of option writers.
- The near-ATM rolling nature of the historical chain remains explicit.
- Expiry identity remains derived.

## Next phase
Use the descriptive output to define deterministic chain interpretations such as potential support/resistance and confirmation/contradiction, then test those interpretations independently before integration into the decision engine.
