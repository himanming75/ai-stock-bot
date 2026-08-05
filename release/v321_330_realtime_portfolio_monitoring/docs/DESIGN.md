# V321–V330 Realtime Portfolio Monitoring

This bundle is independent from the currently running Paper Automation
Controller. It does not modify Controller checkpoints, profiles, locks, or
cycle ledgers.

Stages:

- V321 Account Snapshot
- V322 Position Valuation
- V323 Unrealized PnL
- V324 Filled Order Cash Flow
- V325 Equity, Cash, and Buying Power
- V326 Gross and Net Exposure
- V327 Position Change Detection
- V328 Daily Return
- V329 Append-only Portfolio Ledgers
- V330 Dashboard Snapshot

Important accounting note:

The Alpaca order list does not provide complete realized PnL accounting.
Therefore the bundle records filled buy/sell cash flow without falsely
labeling it as realized profit. Broker account equity, last equity, daily PnL,
positions, and unrealized PnL remain authoritative for this stage.

Safety:

- Alpaca Paper endpoint only
- GET requests only
- no order submission
- no order replacement
- no cancellation
- no Live endpoint
