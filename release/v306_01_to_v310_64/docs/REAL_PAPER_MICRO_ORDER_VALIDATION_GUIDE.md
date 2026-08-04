# V306-V310 Real Paper Micro Order Validation

This stage can submit exactly one Alpaca Paper order:

- Paper endpoint only
- $1 notional by default
- SPY market buy
- DAY time in force
- one lifetime submission token
- deterministic client_order_id
- duplicate prevention
- active-account check
- market-open check
- no-existing-open-order check
- tradable and fractionable asset checks
- order receipt and client-order-id lookup
- Live endpoint, network and submission remain disabled

Three independent actions are required:

1. Enable the one-time token.
2. Pass --allow-paper-network.
3. Pass --submit-one-micro-order.

Installation, tests and dry runs submit zero orders.
