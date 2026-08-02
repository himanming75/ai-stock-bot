# V129.01–V130.00 Existing Paper Order Lifecycle Monitoring Runtime

The runtime repeatedly performs three GET-only reads per poll:

1. Order by client order ID
2. Positions
3. Account

Each observation is appended to a JSONL lifecycle ledger. Transitions record:

- order status change
- filled quantity delta
- position quantity delta
- cash delta
- equity delta

The monitor stops early when the order becomes FILLED, CANCELED, REJECTED, EXPIRED, DONE_FOR_DAY, or REPLACED.

No broker write method is invoked.
