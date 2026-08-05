# V341–V350 Performance Analytics

Inputs:

- V321–V330 portfolio metrics ledger
- V321–V330 latest portfolio snapshot
- V331–V340 latest risk snapshot

Stages:

- V341 Equity Curve
- V342 Period PnL and Returns
- V343 Daily, Weekly, and Monthly Aggregation
- V344 Positive and Negative Period Statistics
- V345 Trade-Level Profit Factor Readiness
- V346 Trade-Level Expectancy Readiness
- V347 Consecutive Positive and Negative Periods
- V348 Sharpe Ratio
- V349 Sortino Ratio and Maximum Drawdown
- V350 Performance Dashboard and Ledger

Accuracy rule:

The current source provides portfolio-equity observations, not a complete
closed-trade realized-PnL ledger. Therefore trade-level Win Rate, Profit
Factor, Average Win/Loss, and Expectancy are not fabricated. Those fields
remain null with an explicit insufficient-data status.

Safety:

- no network
- no broker reads
- no broker writes
- no order submission
- no Controller or runtime file changes
