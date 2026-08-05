# AI Approved Decision to Execution Plan Bridge

This stage converts approved Strategy/Risk/Portfolio decisions into execution
plans using the existing ExecutionIntelligenceV2 engine.

It calculates quantity from approved notional and reference price, then
delegates order type, limit price, slice count, expected slippage, and time
limit decisions to the existing execution engine.

This stage is dry-run only. No broker read, broker write, or order submission
is performed.
