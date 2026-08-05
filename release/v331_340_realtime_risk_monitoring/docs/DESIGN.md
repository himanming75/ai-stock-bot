# V331–V340 Realtime Risk Monitoring

This bundle consumes the latest V321–V330 portfolio snapshot and metrics
ledger. It does not call Alpaca and does not modify the running Controller.

Stages:

- V331 Daily Loss Monitor
- V332 Equity Peak and Drawdown
- V333 Single-Position Concentration
- V334 Gross Exposure
- V335 Net Exposure
- V336 Cash Reserve
- V337 Buying-Power Utilization
- V338 Per-Symbol Risk Score
- V339 Risk Alerts and Ledgers
- V340 Risk Dashboard Snapshot

The portfolio risk score is a monitoring score, not a prediction of future
loss. Hard alerts are evaluated independently from the composite score.

Safety:

- no external network
- no broker reads
- no broker writes
- no order submission
- no Controller, Checkpoint, Lock, or runtime-profile changes
