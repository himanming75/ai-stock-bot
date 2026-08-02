# V128.01–V129.00 Actual Order Lifecycle & Fill Reconciliation Gate

This stage does not assume the existing order has filled.

The gate performs two paths:

- `ACCEPTED/NEW`: remain in `WAITING_ACTIVE_ORDER`; new orders stay blocked.
- `PARTIALLY_FILLED`: remain in `WAITING_PARTIAL_FILL`; validate filled and remaining quantities.
- `FILLED`: compare filled quantity, broker position quantity, and average fill/entry price.
- `CANCELED/REJECTED/EXPIRED`: verify any partial fill against the broker position.
- Unknown status: enter Safe Mode.

The actual runner performs exactly three GET-only reads:

1. Order by client order ID
2. Positions
3. Account

No POST, PATCH, DELETE, order replacement, or cancellation is performed.
