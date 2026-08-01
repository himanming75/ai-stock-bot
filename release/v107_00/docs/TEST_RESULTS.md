# Test Coverage

The unit suite executes:

- BUY fill cash and position updates
- weighted average price
- SELL realized P/L
- unrealized P/L and equity
- partial then full fill incremental accounting
- rejected execution ignore path
- insufficient cash and position rejection
- EventBus snapshot publication
- buying power
- price-book validation
- fill deduplication
- position close reset

## Local validation

- Unit tests: 13/13 PASS
- Portfolio accounting demo: PASS
- Verification: PASS
- Network requests: 0
- Actual paper orders: 0
- Live orders: 0
