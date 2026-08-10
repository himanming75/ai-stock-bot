# Broker Integration V2.1.31.3 — Eligibility Block-Reason Diagnostic

Base commit: `13a08762`.

## Purpose

Explain why the currently running V2.1.31 Paper execution loop reports
`eligible=0`.

This stage is diagnostic-only.

It does not modify:

- current selector
- selector thresholds
- V2.1.31 loop
- order builder
- risk budget
- kill switch
- Paper/live order submission

## Canonical source

The stage reuses V2.2.1's already-shipped selector explanation, which is tied to:

- engine: `multi_timeframe_ai.engine.analyze_symbol`
- selector: `paper_autonomous_execution.signals.select_candidate`

The current selector explanation evaluates:

1. action must be BUY or SELL
2. calibrated confidence must meet current `min_confidence`
3. reward/risk must meet current `min_reward_risk`
4. canonical `ANALYSIS_ONLY` guardrail must be present

## Output

For each symbol:

- eligible TRUE/FALSE
- action
- calibrated confidence
- current minimum confidence
- confidence margin
- reward/risk
- current minimum reward/risk
- reward/risk margin
- exact block-reason list
- shadow quality score
- probability
- market regime
- timeframe details

Runtime files:

`runtime/eligibility_block_reason_diagnostic_v2_1_31_3/`

- `latest_eligibility_diagnostic.json`
- `eligibility_diagnostic_ledger.jsonl`

## Safety

- broker network: OFF
- Paper orders: 0
- Live orders: 0
- thresholds modified: FALSE
- execution selector modified: FALSE
