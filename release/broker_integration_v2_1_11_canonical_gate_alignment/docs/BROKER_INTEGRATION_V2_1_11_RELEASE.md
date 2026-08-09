# Broker Integration V2.1.11 — Canonical Gate Alignment

Base commit: `3c754a88`

## Repository audit

The repository currently defines:

### Signal decision gate
`broker_integration_v1/etrade_ai_signal_decision_v2_1_5.py`

- minimum confidence: `0.60`
- allowed actions: BUY / SELL / HOLD
- HOLD is not order-eligible
- BUY/SELL below minimum confidence become HOLD

### AI promotion gate
`ai_engine_v2/promotion_gate_v3_21.py`

- minimum comparisons: `20`
- aggregate challenger delta P&L must be positive
- challenger drawdown must not be worse
- eligible result is for manual review
- automatic promotion remains false

### AI safety supervisor
`ai_engine_v2/safety_supervisor_v3_29.py`

- live trading locked
- broker write locked
- automatic promotion locked
- automatic strategy change locked
- paper parameter change locked

## Correction

No repository evidence was found for a canonical `.75 confidence + RR >= 1` execution rule in the current branch. V2.1.11 therefore does not introduce either of those values.

## What V2.1.11 adds

A preflight alignment layer that verifies the current canonical contracts before the existing V2.1.10 Sandbox execution bridge is allowed to proceed.

It does not replace:
- V2.1.5 signal gate
- V3.21 promotion gate
- V3.29 safety supervisor
- V2.1.10 execution bridge
- V2.1.4 bounded controller

## Safety

- Sandbox alignment only
- PROD order post remains false
- live trading remains false
- no profitability validation
