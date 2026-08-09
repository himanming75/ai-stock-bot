# Broker Integration V2.1.12 — Canonically Aligned End-to-End Sandbox Runtime

Base commit: `69abd6cc`

## Purpose

Provide one runtime entry point for the already-proven development chain:

`Alpaca read-only historical bootstrap`
→ `existing indicator/signal pipeline`
→ `V2.1.11 canonical alignment`
→ `V2.1.10 eligible signal bridge`
→ `V2.1.4 bounded E*TRADE Sandbox controller`

## Reuse

V2.1.12 does not create new market-data, indicator, signal, gate, order, ledger, or reconciliation engines.

It reuses:
- V2.1.8.2 symbol-scoped Alpaca bootstrap
- V2.1.9 runtime signal pipeline
- V2.1.11 canonical alignment
- V2.1.10 eligible-signal execution bridge
- V2.1.4 bounded controller
- existing E*TRADE Sandbox OAuth/order transports
- existing ledger/reconciliation path inside the cycle engine

## Runtime behavior

### HOLD / zero eligible signals
If there are no eligible signals:
- canonical alignment must still pass
- E*TRADE OAuth is skipped
- Sandbox Preview is skipped
- Sandbox Place is skipped
- broker order count remains zero

### Eligible BUY/SELL signals
The runtime prints the plan first.

The user must explicitly type:
`RUN_CANONICAL_SANDBOX`

Only then may E*TRADE Sandbox OAuth and the existing bounded controller run.

## Existing safety

- maximum Sandbox cycles: 3
- duplicate signal guard reused
- kill switch reused
- stop-on-error reused
- PROD order post remains disabled
- live trading remains disabled
- automatic promotion remains locked
- no profitability validation
