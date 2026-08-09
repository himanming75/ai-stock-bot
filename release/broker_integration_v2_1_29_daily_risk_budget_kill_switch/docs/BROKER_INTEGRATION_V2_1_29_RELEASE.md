# V2.1.29 — Daily Risk Budget + Kill Switch

Base commit: `a67a2e0d`.

This stage does not create a new signal, entry, exit, broker, lifecycle, or reconciliation engine. It wraps V2.1.28 and reads the immutable V2.1.27 completed-round-trip ledger.

Initial Paper validation policy:
- maximum completed round-trips per market day: 2
- maximum daily fill-based loss budget: USD 5.00
- maximum consecutive losing completed round-trips: 2
- manual local kill switch: enabled
- abnormal delegated V2.1.28 status: fail closed and engage kill switch

V2.1.29 delegates at most one completed round-trip to V2.1.28 per call, then recomputes risk before allowing another. This prevents the second trade from starting before the first trade's completed P&L is assessed.

P&L source is explicitly V2.1.27 `FILL_BASED_GROSS_PNL_BEFORE_FEES`; it is not claimed to be broker tax-lot realized P&L.

Install/tests use no broker network and submit zero orders. Live trading remains locked.
