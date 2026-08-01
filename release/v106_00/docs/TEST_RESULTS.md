# Test Coverage

The unit suite executes:

- client order ID generation
- market and limit payload building
- idempotency blocking
- execution request construction
- accepted and rejected mock responses
- partial fill
- full fill after partial fill
- cancel record
- reconciliation match and mismatch
- EventBus execution flow
- EventBus rejected flow
- confirmation that the mock transport is in-memory
