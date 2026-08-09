# V2.1.28 — Continuous Bounded Paper Session + Safe Cycle Rollover

Base commit: `cb118f91`.

## What this stage adds

V2.1.28 does **not** rebuild entry, exit, lifecycle, signal, or reconciliation logic.

It reuses:

- V2.1.26 — full recovery-aware Paper round-trip orchestrator
- V2.1.27 — final exit fill reconciliation and completed round-trip ledger

The only new responsibility is:

`ROUND_TRIP_COMPLETE -> verified rollover -> fresh IDLE current-cycle state -> next V2.1.26 round-trip`

## Rollover proof requirements

A rollover is allowed only when all are true:

1. V2.1.26 state says `round_trip_complete = true`
2. `final_round_trip_id` exists
3. `final_fill_reconciled = true`
4. that same round-trip ID exists in V2.1.27 `completed_round_trips.jsonl`

If any proof is missing, rollover is blocked.

## What rollover changes

Only:

`runtime/full_alpaca_paper_round_trip_v2_1_26/cycle_state.json`

is reset to a fresh IDLE current-cycle state.

Historical ledgers from V2.1.22, V2.1.23, V2.1.25, V2.1.26, and V2.1.27 are preserved.

The new state retains:

`prior_completed_round_trip_id`

for audit continuity.

## Continuous session behavior

The supervisor performs only these existing-stage transitions:

- call V2.1.26 for the current round-trip
- if exit was submitted, call V2.1.27 for final read-only reconciliation
- when V2.1.27 completes, verify rollover proof
- rollover current-cycle state
- start the next V2.1.26 round-trip

## Bounded safety

Default maximum completed round-trips per session: **2**

Hard maximum accepted by the controller: **3**

This is intentionally not unlimited continuous trading.

V2.1.29 will add the dedicated daily risk budget / loss budget / kill-switch layer before broader autonomous Paper operation.

## DRY mode

Default mode.

No broker order execution methods are invoked by V2.1.28 itself. Existing V2.1.26 DRY behavior is reused.

Installation/tests:
- broker network: OFF
- actual Paper orders: 0
- live orders: 0

## PAPER mode

Requires explicit:

`RUN_BOUNDED_CONTINUOUS_ALPACA_PAPER_SESSION`

Existing V2.1.22 and V2.1.25 Paper-only guards remain authoritative.

## Live

Live trading remains locked.

## Next stage

V2.1.29 — Daily Risk Budget + Kill Switch.
