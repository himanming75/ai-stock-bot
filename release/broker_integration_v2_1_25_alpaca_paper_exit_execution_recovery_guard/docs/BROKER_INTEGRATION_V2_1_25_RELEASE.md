# V2.1.25 — Alpaca Paper Exit Execution + Restart/Recovery Guard

Base commit: `d29a37be`.

## Purpose

Connect the existing V2.1.23 read-only `EXIT_READY` state to a one-time Alpaca Paper position close while preserving restart/idempotency safety.

## Existing components reused

- V2.1.23 lifecycle result and existing exit-rule decision
- `PaperAutonomousExecutionService.preflight()`
- existing Alpaca adapter/client created with `paper=True`

The exit write uses Alpaca-py's official `TradingClient.close_position(symbol)` call. No live client is created.

## Required guards

An exit can proceed only when:
- V2.1.23 status is `PASS_ORDER_POSITION_LIFECYCLE_READ_ONLY`
- lifecycle state is `POSITION_EXIT_READY_READ_ONLY`
- exit decision action is `EXIT`
- symbol/evidence binding exists
- exit fingerprint has not already been submitted
- explicit `CLOSE_ALPACA_PAPER_POSITION_ONCE` confirmation is provided
- existing Paper preflight passes
- the position still exists in the Alpaca Paper account

## Restart/recovery

A durable JSONL exit ledger records submitted exit fingerprints.

On restart:
- an already-submitted fingerprint is blocked
- if the position is already absent, the system records `RECOVERED_POSITION_ALREADY_CLOSED_NO_DUPLICATE_EXIT` and submits nothing
- local recovery inspection uses no broker network

## Safety

Installation/tests:
- broker network: OFF
- Paper exit orders: 0
- Live orders: 0

Actual execution:
- Alpaca Paper only
- one position close per unique exit fingerprint
- existing Paper arm/preflight retained
- live trading locked
- E*TRADE write unchanged/off

## Next stage

V2.1.26 will integrate entry + lifecycle + exit into one full Paper trading cycle and add recovery-aware continuation.
