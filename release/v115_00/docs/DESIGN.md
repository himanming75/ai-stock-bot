# V114.01–V115.00 Alpaca Paper Session Scheduler Foundation

Implemented:

- New York market timezone handling
- Pre-market, regular, after-hours, closed, weekend, and holiday phases
- PREPARE, START_SESSION, RUN_CYCLE, CLOSE_SESSION, RECOVER_SESSION, WAIT, and SKIP_DAY actions
- Atomic scheduler state persistence
- New-day reset
- Regular-session restart recovery
- Stale active-session closure
- Configurable cycle and polling intervals
- Heartbeat and cycle counters
- Zero broker network access
- Zero order submission

This release provides scheduling logic only. Broker calendar synchronization and runtime integration remain separate later stages.
