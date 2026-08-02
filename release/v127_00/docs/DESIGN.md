# V126.01–V127.00 Controlled Autonomous Paper Single Order

This stage introduces the first actual autonomous Paper submission path, but it is fail-closed.

Before any POST, the runner verifies:

1. V126 `PAPER_WRITE_READY` certificate
2. exact order-submission approval
3. Paper account ACTIVE
4. trading not blocked
5. market open
6. approved symbol
7. BUY/SELL side
8. quantity no more than 1
9. estimated notional no more than $100
10. MARKET order
11. DAY time in force
12. zero currently open orders

The actual account currently has one recovered Legacy Bot AAPL order. Therefore, the expected actual result is `EXISTING_ORDER_WAIT` with zero writes and zero new orders.

No new order should be submitted until the existing order reaches a terminal state or is resolved through a separately controlled lifecycle policy.
