# TradeCompass Phase 10.19 — Option Type Normalization Fix

This patch fixes a data-schema integration issue discovered during Phase 10.18 analysis.

The reconstructed historical CSV may use broker-style option type labels `CE` / `PE`, while the intelligence layer expects `CALL` / `PUT`. The previous code therefore produced empty Call/Put sets and consequently `None` PCR and ΔOI statistics.

This patch normalizes:
- CE -> CALL
- PE -> PUT
- CALL -> CALL
- PUT -> PUT

No trading rules, thresholds, data rows, or backtest logic are changed.

After merging:
1. `py -m pytest -q`
2. `py -m scripts.run_option_chain_intelligence`
3. `py -m scripts.analyze_option_chain_intelligence`
