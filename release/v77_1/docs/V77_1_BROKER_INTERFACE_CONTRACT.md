# V77.1 Broker Interface Contract

## Purpose
Define the immutable interface that every future sandbox broker adapter must implement.

## Source anchors
- V76.24 closure SHA256: `c8b61f2dbe7150f52a9cfbc52edc7461639584a892aed994c1430930a088eeaf`
- V76.24 closure-chain SHA256: `f82709c71f19252ac423c26b36be1554e7fdc6a0aa4616a3fb52b3b23258f47d`
- Framework commit before installation: `2fc6f54`

## Contract components
- Offline, sandbox and live environment enumeration
- Order side, type, time-in-force and lifecycle statuses
- Immutable order request and normalized broker order models
- Position, account snapshot, health and capability models
- Runtime-checkable `BrokerContract` protocol
- Strict financial validation using `Decimal`
- Terminal order-state definition
- Default offline safety policy

## Safety boundary
V77.1 performs no network call, authenticates no broker, submits no order and does not authorize live trading.

## Next phase
`V77.2 Sandbox Broker Adapter`
