# Bundle B — R11 to R13 Broker / Multi-Account

This package combines the broker and account preparation stages.

## R11 Broker Adapter Interface

Provides a common adapter contract, capability reporting, offline candidate
validation, and a hard-disabled `submit_order` path.

Alpaca is represented as the currently prepared broker because the project
already contains Alpaca Paper execution and read layers. Bundle B itself does
not connect to Alpaca.

E*TRADE, IBKR, and Schwab are represented only by future adapter interfaces.
No claim is made that credentials, network authentication, account reads, or
order submission are implemented.

## R12 Multi-Account Registry / Orchestrator

Provides account definitions with independent:

- broker;
- Paper/Live mode;
- trading profile;
- allocation weight;
- account notional limit;
- credential vault mode;
- enabled state.

Only the primary Alpaca Paper account is enabled in the default preparation
registry. Live and future broker accounts remain disabled.

## R13 Capability Matrix / Order Routing

Routes Bundle A order candidates through account policy and broker capability
checks. Routing is preview-only and every route keeps `submit_allowed=false`.

No broker connection, network call, write operation, or order submission occurs.
