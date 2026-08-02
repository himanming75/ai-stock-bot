# V130.01–V131.00 Order Completion & Next Order Unlock Gate

The gate consumes the latest actual lifecycle monitor result.

States:

- `ACCEPTED/NEW/PENDING_*` → `LOCKED_ACTIVE_ORDER`
- `PARTIALLY_FILLED` → `LOCKED_PARTIAL_FILL`
- `FILLED` with consistent quantities and position → `UNLOCKED_FILLED`
- `CANCELED/REJECTED/EXPIRED/DONE_FOR_DAY/REPLACED` → `UNLOCKED_TERMINAL_NO_FILL`
- Unknown or inconsistent terminal state → `SAFE_MODE`

A local `ORDER_COMPLETED` ledger entry is written only after a terminal state is verified.

This stage performs no broker network operation and no order write.
