# V102.01–V103.00 Real-Time Market Data Foundation

Implemented real reusable market-data components:

- Quote, Trade, and Bar domain models
- Alpaca websocket message parser
- subscription registry
- sequence and duplicate guard
- freshness and future-timestamp validation
- connection state machine
- exponential reconnect backoff
- EventBus routing
- deterministic offline fixture stream
- optional isolated Alpaca websocket runner

The standard run remains offline and creates no broker order.
