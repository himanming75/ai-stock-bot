# Test Coverage

The unit suite executes:

- normal approval
- kill switch halt
- emergency stop halt
- new-buy suspension
- maximum open positions
- total and symbol exposure limits
- SELL handling while new buys are disabled
- daily loss protection
- drawdown emergency stop
- consecutive-loss protection
- profitable reset
- EventBus decision flow
- EventBus portfolio snapshot flow
- session reset

## Local validation

- Unit tests: 15/15 PASS
- Runtime risk manager demo: PASS
- Verification: PASS
- Network requests: 0
- Actual paper orders: 0
- Live orders: 0

The demo order notional is rejected by the per-symbol exposure gate before the total-exposure gate, which is the intended validation order.
