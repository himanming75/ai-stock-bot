# V311-V320 Real Paper Autonomous Data Collection

This stage is monitor-only.

It automatically collects:

- Alpaca Paper account state
- market clock
- open positions
- open orders
- recent closed orders
- order-status distribution
- daily P/L
- unrealized P/L
- position changes
- order-status changes
- snapshot, metrics and reconciliation ledgers

Safety:

- zero new orders
- Paper submission disabled
- Live submission/network disabled
- Broker write disabled
- Paper endpoint only

The collector can run once or repeatedly during the market session.
