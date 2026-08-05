# Market Intelligence Data Fusion Mega Bundle

## Scope

This development-only bundle provides an offline-first standard layer for:

- price and volume features
- market breadth and sector strength
- news sentiment and importance
- earnings surprise and estimate revisions
- macro and rates risk
- options put/call, IV rank, and directional flow
- liquidity, spread, event risk, freshness, and confidence
- market regime classification
- risk-on/risk-off mode
- symbol ranking and trade bias
- machine-readable dashboard snapshot

## Safety invariants

- No external network access
- No broker reads
- No broker writes
- No paper order submission
- No live order submission
- Validation track is unchanged
- P3 remains a separate market-dependent action

## Pipeline

Input adapters -> normalized FusionInput -> quality gate -> regime classifier
-> component scoring -> risk penalty -> symbol ranking -> MarketContext JSON.

## Integration target

The produced `market_intelligence_snapshot.json` is designed to feed the
existing Strategy Ensemble V4, Adaptive Risk Engine V3, Portfolio
Intelligence V2, Execution Intelligence V2, and dashboard layers.
