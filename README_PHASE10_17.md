# TradeCompass Phase 10.17 — Historical Option-Chain Intelligence

## Purpose
Build an independent, deterministic historical option-chain evidence layer before allowing any chain metric to influence BUY CALL / BUY PUT / WAIT.

## What this phase calculates
- Call/Put contract coverage per timestamp
- Common-strike intersection
- Call OI and Put OI over common strikes
- PCR based on common strikes only
- Highest Call OI / Put OI concentration and percentage
- Distance of OI peaks from spot
- Aggregate Call/Put ΔOI
- Strike with the largest positive ΔOI on each side
- ATM strike and ATM Call/Put IV/OI
- Coverage completeness and derived-identity status

## Integrity rules
1. Only rows from the requested timestamp are used.
2. Exact acquisition-boundary duplicates are deduplicated without changing market values.
3. Conflicting duplicates are rejected rather than silently selected.
4. ΔOI is calculated only against the immediately preceding processed timestamp and the same expiry + strike + option type.
5. No future or end-of-day data is used.
6. PCR uses only the common Call/Put strike intersection, avoiding artificial bias from asymmetric rolling windows.
7. Missing strikes are not fabricated as zero.
8. Large OI is described as concentration/potential positioning, not proof of writers.
9. Historical expiry identity is not repaired or re-inferred here.
10. This phase does not change the trading strategy, option selector, risk engine, or backtester.

## Run tests
```powershell
py -m pytest -q
```

## Build the independent historical layer
```powershell
py -m scripts.run_option_chain_intelligence
```

The default input is:
`data/dhan_history/reconstructed/nifty_fixed_contracts_1y.csv`

The output is:
`data/dhan_history/reconstructed/option_chain_intelligence_1y.json`

## What comes next
After this layer is validated on the actual one-year dataset, we can define and test deterministic chain interpretations (for example potential support/resistance and confirmation/contradiction) separately. Only after those tests should the chain layer be integrated into the TradeCompass decision engine and compared against the no-chain baseline.
