# V119.01–V120.00 Autonomous Alpaca Paper Runtime Foundation

Implemented:

- approved-symbol lock: AAPL, SPY, QQQ
- quantity hard limit of one
- maximum notional of $100
- fractional-order rejection
- live-trading rejection
- market-open gate
- BUY-signal gate
- read-network opt-in dependency
- preview-only default behavior
- explicit single-order Paper write opt-in
- one-order submission path for controlled test doubles
- zero Live-order capability
- offline fixture validation

The default demo enables simulated read access but keeps Paper write access disabled, so it produces only an order preview.
