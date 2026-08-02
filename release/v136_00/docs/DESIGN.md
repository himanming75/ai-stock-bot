# V135.01–V136.00 Controlled Autonomous Next-Order Cycle

This stage consumes the actual V135 readiness result and controls creation of at most one local next-order cycle token.

Behavior:

- Blocked readiness state: WAIT, no token.
- READY: validate symbol, side, quantity, estimated price, and notional cap.
- Valid READY: write one deterministic cycle token and produce a single-order preview-ready state.
- Same cycle repeated: DUPLICATE_CYCLE, no second token.
- Different token already present or inconsistent readiness: Safe Mode.

No Alpaca network call and no order submission occurs in this stage.
