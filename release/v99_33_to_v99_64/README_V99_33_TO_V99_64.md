# V99.33-V99.64 Portfolio Rebalance Engine & Trade Intent Generator

## Included

- V99.33-V99.40 current versus target strategy-weight model
- V99.41-V99.48 rebalance threshold and trade-intent planning
- V99.49-V99.56 turnover cap, cash-reserve projection and duplicate blocking
- V99.57-V99.64 risk gate, audit ledger, SHA-256 certificate, tests and release

All trade intents are planning artifacts only. Execution authorization, broker writes, network access and order submission remain disabled.

## Cash-reserve protection

Rebalance planning processes SELL intents before BUY intents and limits BUY notional so projected cash cannot fall below the configured minimum.
