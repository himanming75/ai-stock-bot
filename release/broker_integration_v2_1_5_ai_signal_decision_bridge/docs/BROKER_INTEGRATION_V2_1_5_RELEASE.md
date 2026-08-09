# Broker Integration V2.1.5 — AI Signal Decision Bridge

Base commit: `bd406a36`

## Why this stage is a bridge
The existing AI Engine V2 has strategy registry, regime selection, portfolio intelligence and safety supervision, but it does not currently produce an executable BUY/SELL/HOLD order signal.

V2.1.5 therefore does not invent a trading strategy. It accepts a strategy recommendation payload and validates/normalizes it for the existing Sandbox execution path.

## Input contract
Required:
- symbol
- action: BUY / SELL / HOLD
- confidence: 0..1
- quantity
- strategy_id

## Decision policy
- Default minimum confidence: 0.60
- HOLD never creates an order
- BUY/SELL below confidence threshold become HOLD
- Maximum eligible signal queue: 3
- V2.1.4 bounded controller remains the execution boundary

## Reuse / no duplication
Reuses:
- V2.1.3 `SandboxCycleSignal`
- V2.1.4 bounded multi-cycle controller
- V2.1 Preview/Place
- V2.1.2 ledger/reconciliation
- canonical V77.1 order contract

AI Engine V2 is not modified in this stage.

## Safety
- Development/synthetic verification only in this package
- No broker network used by build/test
- Sandbox execution remains separate
- PROD orders locked
- Live trading locked
- Profitability is not validated or inferred
