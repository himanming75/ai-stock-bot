# Release Notes

V122.01–V123.00 adds open-order ownership and identity reconciliation.

The current unexplained open-order condition is represented as an EXTERNAL order in the offline fixture, keeping Safe Mode engaged. An optional GET-only actual runner is included to determine the real order's client_order_id, symbol, side, quantity, type, and status.
