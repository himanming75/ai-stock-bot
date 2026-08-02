# V134.01–V135.00 Autonomous Next-Order Readiness Gate

The gate evaluates whether another autonomous Paper order may begin.

Required conditions:

- no active/open order
- terminal state committed when applicable
- no upstream Safe Mode
- broker account ACTIVE
- trading_blocked=false
- market open
- runtime risk approved
- position count within cap
- total market value within cap

The actual runner performs four GET-only reads:

1. Account
2. Open orders
3. Positions
4. Clock

No order write is possible.
