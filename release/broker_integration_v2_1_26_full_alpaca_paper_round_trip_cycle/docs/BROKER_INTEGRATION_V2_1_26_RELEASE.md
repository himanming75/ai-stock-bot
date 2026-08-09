# V2.1.26 — Full Alpaca Paper Round-Trip Cycle

Base commit: `caf482b7`.

## Purpose

Integrate the already-built Broker Integration chain into one recovery-aware Paper trading cycle:

1. V2.1.21 actual intraday canonical READY validation
2. V2.1.22 bounded Alpaca Paper entry
3. V2.1.23 read-only order/position lifecycle
4. V2.1.25 one-time Alpaca Paper exit + restart/recovery guard

No new market-data engine, signal engine, broker adapter, order engine, or exit strategy is introduced.

## Durable state machine

V2.1.26 persists:

- current phase
- evidence key
- symbol
- entry-submitted state
- entry client-order id
- position-observed state
- exit-ready state
- exit-submitted state
- round-trip-complete state
- Paper entry/exit counts

On restart, the controller checks durable state first. If an entry was already submitted, it resumes lifecycle/exit handling instead of searching for another entry.

## Limits

Per V2.1.26 round-trip:

- Paper entries: maximum 1
- Paper exits: maximum 1
- Live orders: 0

V2.1.22 and V2.1.25 duplicate guards remain authoritative.

## DRY mode

DRY mode is the default.

It can build entry/exit plans but never invokes either order-execution method.

Installation and automated tests use:
- broker network: OFF
- actual Paper orders: 0
- live orders: 0

## PAPER mode

PAPER mode requires explicit:

`RUN_FULL_ALPACA_PAPER_CYCLE`

It also retains:
- Alpaca Paper endpoint verification
- existing V2.1.22 entry confirmation/one-time evidence guard
- existing Paper arm/preflight requirement
- existing V2.1.25 one-time exit fingerprint guard
- already-closed-position restart recovery
- live trading OFF

## Current completion boundary

After V2.1.25 submits the exit order, V2.1.26 records:

`EXIT_SUBMITTED_AWAITING_FINAL_FILL`

Final exit fill reconciliation and immutable completed round-trip P&L ledger are intentionally deferred to V2.1.27.

## Next stage

V2.1.27 — Final Exit Fill Reconciliation + Completed Round-Trip Ledger.
