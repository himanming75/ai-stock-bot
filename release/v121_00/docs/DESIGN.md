# V120.01–V121.00 Actual Autonomous Paper Read Session

The read session gathers one autonomous Paper account snapshot through five GET operations:

1. Account
2. Market Clock
3. Positions
4. Open Orders
5. Closed Orders

Safety controls:

- Paper API URL lock
- read opt-in required
- write capability must remain disabled
- exactly five GET methods required
- any write counter causes failure
- account ID redaction
- closed-order limit constrained to 1–500
- actual Paper and Live order counters remain zero
- optional actual runner requires Paper credentials and exact confirmation text

The standard pipeline uses an offline fixture. The optional actual runner performs GET-only requests against the Alpaca Paper API.
