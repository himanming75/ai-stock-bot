# Broker Integration V1 Bridge

Base commit: `cd826dcb`

This stage is deliberately a **bridge**, not a new broker engine.

## Non-duplication rules

The repository already contains the canonical broker contract in:

`broker/contracts_v77_1.py`

Broker Integration V1 imports and reuses its:
- AccountSnapshot
- BrokerCapabilities
- BrokerContract
- BrokerEnvironment
- BrokerHealth
- BrokerOrder
- BrokerOrderRequest
- BrokerOrderStatus
- BrokerPosition
- BrokerSafetyPolicy
- OrderSide
- OrderType
- TimeInForce

It does not recreate those contracts.

The existing `alpaca_market_data` stack is also reused. No replacement Alpaca market-data client is created.

## E*TRADE foundation

The E*TRADE Developer Platform uses OAuth 1.0a with HMAC-SHA1 for the retail developer API.

V1 adds only:
- OAuth/API profile metadata
- credential isolation contract
- NoNetworkTransport default
- fixture transport for software tests
- read-only account/balance/portfolio/order normalization
- canonical V77.1 AccountSnapshot output
- broker capability matrix
- live safety gateway

V1 does NOT:
- read real E*TRADE credentials
- perform OAuth authorization
- use E*TRADE network
- submit, cancel, or replace orders
- enable Live trading

## Dashboard

Adds bilingual Broker Integration V1 status:
- Development
- Canonical Contract reuse
- E*TRADE Read-only foundation
- Network lock
- Live lock
- Duplicate component audit
- Broker capability matrix

## Commercial note

The E*TRADE developer terms distinguish personal/non-commercial API use from commercial distribution. This build is an internal/read-only technical foundation only; it does not enable a SaaS/commercial E*TRADE integration.

## Next gate

A later stage may add explicit user-authorized E*TRADE OAuth connectivity and bounded read-only network smoke tests. That must be a separate opt-in gate and must not unlock broker writes.
