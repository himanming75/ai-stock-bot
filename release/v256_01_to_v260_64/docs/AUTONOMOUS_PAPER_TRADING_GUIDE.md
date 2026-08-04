# V256-V260 Autonomous Paper Trading

This stage connects:

- AI Strategy Ensemble V3
- Risk Engine V2
- Execution Optimizer
- Alpaca Paper account, clock, positions and open orders
- Paper order submission
- Idempotency
- Session ledger
- Daily report
- Web API foundation

Safety defaults:

- Autonomous cycle disabled
- Real Paper submission disabled
- Confirmation token invalid
- Live submission disabled
- Live network disabled
- Broker write disabled

Activation requires all of the following:

1. Alpaca Paper credentials in environment variables
2. autonomous_cycle_enabled = true
3. real_paper_submission_enabled = true
4. confirmation file enabled with exact phrase ENABLE_AUTONOMOUS_PAPER
5. market open
6. Execution plan allowed
7. Risk gate passed
8. Network-authorized run script

The code only accepts https://paper-api.alpaca.markets.
