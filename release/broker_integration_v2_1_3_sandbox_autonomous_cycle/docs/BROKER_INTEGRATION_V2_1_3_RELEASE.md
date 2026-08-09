# Broker Integration V2.1.3 — E*TRADE Sandbox Autonomous Cycle

Base commit: `dda6f1a7`

## Purpose
Run one complete E*TRADE Sandbox order lifecycle automatically after one explicit `RUN_ONCE` confirmation.

Flow:
1. OAuth
2. Sandbox account selection
3. signal input
4. canonical BrokerOrderRequest
5. Preview
6. Sandbox Place
7. existing order ledger
8. existing Orders read-back
9. existing reconciliation
10. result summary

## Non-duplication
V2.1.3 reuses:
- canonical `broker.contracts_v77_1.BrokerOrderRequest`
- V2.1 Preview/Place pipeline
- V2.1.2 JSONL ledger
- V2.1.2 Orders reader
- V2.1.2 reconciliation engine
- existing OAuth signer/flow

No replacement order engine, ledger, or reconciliation engine is created.

## Safety
- Sandbox only
- one cycle only
- automatic repeat disabled
- explicit `RUN_ONCE` confirmation required
- PROD order POST locked
- live trading locked
- no real securities or money
- no profitability validation

## Next stage
After V2.1.3 real Sandbox one-cycle verification, the next safe stage is a bounded multi-cycle scheduler with hard cycle limits, cooldown, duplicate-signal protection, and kill switch. It should remain Sandbox-only.
