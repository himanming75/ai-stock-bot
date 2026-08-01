# V104.01–V105.00 Order Intent & Position Sizing Foundation

Implemented real broker-independent execution planning components:

- validated order intent model
- cash-based BUY sizing
- position-based SELL sizing
- maximum quantity and notional limits
- fractional quantity normalization
- slippage buffer
- intent expiration
- duplicate intent guard
- `strategy.signal` to `order.intent` EventBus bridge
- intent engine statistics

This stage does not call a broker and does not submit an order.
