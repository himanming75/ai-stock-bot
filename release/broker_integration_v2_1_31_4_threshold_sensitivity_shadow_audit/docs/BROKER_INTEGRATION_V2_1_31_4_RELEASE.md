# Broker Integration V2.1.31.4 — Threshold Sensitivity Shadow Audit

Base commit: `8b607018`.

## Purpose

Determine whether the current confidence threshold of 0.75 is overly restrictive
without changing actual Paper execution.

Shadow confidence thresholds:

- 0.60
- 0.65
- 0.70
- 0.75 (current execution threshold)

Reward/risk remains fixed at 1.0.

## Data source

Existing V2.2.1 feature snapshot ledger:

`runtime/ai_signal_scoring_feature_snapshot_v2_2_1/feature_snapshot_ledger.jsonl`

The audit uses the canonical selector inputs already captured in each feature snapshot:

- action
- calibrated confidence
- reward/risk
- timeframe closes

## Counterfactual signal

A threshold-level signal exists only when:

- action is BUY or SELL
- reward/risk >= 1.0
- calibrated confidence >= the shadow threshold

The current actual selector is not changed.

## Outcome resolution

For each hypothetical signal, later snapshots for the same symbol are searched at
5, 15, 30 and 60 minutes, with up to 3 minutes of timing tolerance.

Outcome is direction-aware snapshot price return:

- BUY: future/entry - 1
- SELL: -(future/entry - 1)

This is **not broker fill P&L** and does not model spread, slippage, commissions,
position sizing or fill uncertainty.

## Continuous collection

`START_V2_1_31_4_CONTINUOUS_THRESHOLD_AUDIT.ps1`

runs snapshot refresh + audit once per minute for up to 8 hours.

Stop:

`STOP_V2_1_31_4_CONTINUOUS_THRESHOLD_AUDIT.ps1`

## Safety

- Actual confidence threshold: 0.75, unchanged
- Actual selector modified: FALSE
- Broker network from audit: OFF
- Orders from audit: 0
- Live trading: LOCKED
