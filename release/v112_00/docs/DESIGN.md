# V111.01–V112.00 Controlled Alpaca Paper Single-Order Opt-In

Safety constraints:

- Paper Trading domain only
- exact write opt-in required
- exact confirmation phrase required
- allowlist: AAPL, SPY, QQQ
- maximum quantity: 1 share
- maximum estimated notional: $100
- market/day orders only
- one use per process
- active, unblocked Paper account required
- market must be open
- no existing open orders
- BUY blocked when the same symbol is already held
- bounded request timeout
- no automatic retry for POST
- live order count always zero

The standard pipeline is an offline fixture. The actual runner is separate.
