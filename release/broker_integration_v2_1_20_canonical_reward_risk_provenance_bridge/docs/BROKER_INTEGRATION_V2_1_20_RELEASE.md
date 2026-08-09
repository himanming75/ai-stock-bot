# Broker Integration V2.1.20 — Canonical Reward/Risk Provenance Bridge

Base commit: `a315dc5c`

## Purpose

Bridge the existing Canonical Paper engine's reward/risk output into the Broker Integration evidence chain without inventing a new RR formula.

## Authoritative existing source

The repository's existing real-market multi-timeframe shadow uses:

- `multi_timeframe_ai.engine.analyze_symbol`
- `paper_autonomous_execution.signals.select_candidate`
- minimum calibrated confidence `0.75`
- minimum reward/risk `1.0`

The canonical analyzer already emits `reward_risk`.

V2.1.20 therefore does **not** reconstruct reward/risk from guessed Entry/Stop/Target values.

## Sources

Input evidence:

`runtime/fresh_eligible_signal_evidence_v2_1_16/eligible_signal_evidence.jsonl`

Canonical analysis snapshot:

`runtime/real_market_multitimeframe_shadow/latest_real_market_shadow.json`

## Join contract

For each V2.1.16 eligible signal:

1. Symbol must exist in canonical analyses.
2. Canonical action must equal evidence side.
3. Canonical calibrated confidence must exist.
4. Canonical reward/risk must exist.
5. Canonical engine / selector / thresholds must match the repository contract.

The bridge records:

- original generic source confidence
- canonical calibrated confidence
- canonical reward/risk
- canonical snapshot SHA-256
- canonical analysis SHA-256
- source dataset path
- engine / selector names
- threshold contract

## V2.1.17 correction

V2.1.17 now reads:

`runtime/canonical_reward_risk_provenance_v2_1_20/enriched_evidence.jsonl`

instead of directly reading V2.1.16 evidence.

It also requires:

- `canonical_reward_risk_provenance_valid == True`
- `reward_risk_formula_recomputed == False`

## Safety

This stage:
- makes no market-data request
- starts no E*TRADE OAuth
- sends no Sandbox Preview
- sends no Sandbox Place
- submits no broker order
- enables no PROD order
- enables no live trading

## Expected current-runtime behavior

If V2.1.16 has no eligible evidence yet:

`WAITING_FOR_V2_1_16_EVIDENCE`

If the canonical real-market snapshot has not been generated:

`WAITING_FOR_CANONICAL_REAL_MARKET_SNAPSHOT`

Both are safe waiting states.
