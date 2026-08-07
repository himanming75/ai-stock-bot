# Paper Trading Completion Track — 1 of 5

This stage is fixed as:

1. Execution Integration — this bundle
2. Order and Position Lifecycle
3. Autonomous Session Orchestrator
4. Restart and Recovery
5. End-to-End Paper Certification

No additional stages are inserted before Paper Trading 1.0 operation.

## Safety

- Alpaca Paper only
- Live submission hard OFF
- One validation order per session
- Maximum notional $25
- Allowed-symbol list
- Confidence and reward/risk filters
- Market-open requirement
- Manual PAPER_ONLY arm token
- Build and test submit zero orders

## Tomorrow workflow

1. Install requirements, including alpaca-py.
2. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY for the Paper account.
3. Run TEST.
4. Run PREFLIGHT before the market opens.
5. After the market opens, run ARM.
6. Run one Paper validation order.
7. Review the Paper account and ledgers before any continuous session work.
