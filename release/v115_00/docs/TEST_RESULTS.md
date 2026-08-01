# Test Coverage

- pre-market preparation
- regular open and cycle execution
- after-hours close
- weekend and holiday skip
- persisted scheduler state
- active-session restart recovery
- stale-session closure
- new-day reset
- closed-market wait
- network/write/order counters remain zero
- configuration validation
- timezone-aware datetime enforcement

## Local validation

- Unit tests: 13/13 PASS
- Session scheduler demo: PASS
- Verification: PASS
- Network requests: 0
- Write requests: 0
- Actual Paper orders: 0
- Live orders: 0
