# Test Coverage

The unit suite executes:

- Quote, Trade, and Bar parsing
- ignored control frames
- crossed-quote rejection
- subscription changes
- duplicate and out-of-order sequence handling
- stale/future data detection
- valid and invalid connection transitions
- reconnect delay capping and reset
- EventBus routing
- end-to-end fixture stream

## Local validation

- Unit tests: 13/13 PASS
- Offline fixture stream: PASS
- Verification: PASS
- Network connections: 0
- Broker orders: 0
