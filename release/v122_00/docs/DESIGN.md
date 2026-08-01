# V121.01–V122.00 Autonomous Paper Read Reconciliation

The reconciler compares the actual Alpaca Paper read snapshot with:

- internal cash
- internal equity
- internal positions
- internal held symbols
- internal open-order count
- recovery snapshot generation
- runtime state

Blocking mismatches engage Safe Mode and set `autonomous_order_allowed` to false.

The demonstration intentionally compares the actual account's one open order with an internal expected open-order count of zero. This validates that an unexplained open order blocks autonomous execution.
