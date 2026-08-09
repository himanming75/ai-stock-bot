# V2.1.27 — Final Exit Fill Reconciliation + Completed Round-Trip Ledger

Base commit: `4b8c4008`.

## Purpose

Close the remaining accounting/reconciliation gap after V2.1.26.

V2.1.27 combines:

- V2.1.23 actual entry order fill
- V2.1.25 submitted exit order
- actual Alpaca Paper exit order state
- actual post-exit position state

into one immutable completed round-trip record.

## Existing components reused

The existing `AlpacaPaperReadClient` is reused for:

- exit order lookup by `client_order_id`
- positions
- account
- market clock

That existing client hard-blocks any endpoint other than:

`https://paper-api.alpaca.markets`

V2.1.27 creates no broker write path.

## Why the existing entry lifecycle monitor is not reused unchanged

The existing entry lifecycle monitor treats a filled order as consistent only if
the matching position exists. That is correct for a BUY entry.

For a full exit, the desired invariant is the opposite:

- exit order status = filled
- exit filled quantity > 0
- exit average fill price exists
- broker order ID matches the V2.1.25 submitted exit
- no matching position remains after the full close

Therefore V2.1.27 reuses the existing Paper read client and terminal-status
definitions, but applies exit-specific reconciliation semantics.

## Completed round-trip ledger fields

Each completed row records:

- round-trip ID
- evidence key
- symbol
- entry client/broker order IDs
- entry actual filled quantity
- entry actual average fill price
- entry submitted/fill timestamps
- exit client/broker order IDs
- exit actual filled quantity
- exit actual average fill price
- exit submitted/fill timestamps
- exit reason
- quantity reconciliation
- holding seconds
- fill-based gross P&L
- fill-based return percentage

P&L is explicitly labeled:

`FILL_BASED_GROSS_PNL_BEFORE_FEES`

No fee-inclusive or broker-tax-lot realized P&L claim is made.

## Idempotency

`round_trip_id` is derived from the evidence key plus entry and exit order IDs.

A completed round trip cannot be appended twice.

## V2.1.26 completion

After successful exit fill reconciliation, V2.1.27 updates the V2.1.26 durable
state to:

- phase = `ROUND_TRIP_COMPLETE`
- round_trip_complete = true
- final_fill_reconciled = true

## Safety

Installation/tests:
- broker network: OFF
- Paper orders: 0
- Live orders: 0

Actual reconciliation:
- Paper reads only
- broker writes: 0
- Paper orders submitted by V2.1.27: 0
- Live trading: OFF

## Next stage

V2.1.28 — Continuous Multi-Round-Trip Paper Session.
