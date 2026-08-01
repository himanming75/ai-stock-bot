# V113.01–V114.00 Alpaca Paper Order Recovery & Restart

This release adds crash-safe recovery for one already submitted Paper order.

- Atomic JSON checkpoint with `os.replace`
- Schema and field validation
- Persisted client order ID, broker ID, side, quantity, fill progress, and status
- Fresh-process restart simulation
- GET-only recovery by `client_order_id`
- Filled quantity monotonicity validation
- Symbol, side, and quantity identity validation
- Recovery generation counter
- Terminal and recoverable status classification
- Duplicate submission prevention
- Write-enabled clients rejected
- Zero POST and DELETE requests during recovery

The standard pipeline is fully offline. The optional actual recovery runner is read-only.
