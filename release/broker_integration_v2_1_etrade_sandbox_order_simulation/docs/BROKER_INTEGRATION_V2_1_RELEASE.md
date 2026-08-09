# Broker Integration V2.1 — E*TRADE Sandbox Order Simulation

Base commit: `92f68185`

## Purpose
Validate the E*TRADE automated order pipeline in Sandbox without real securities or money.

## Reuse / no duplication
Reuses:
- `broker.contracts_v77_1.BrokerOrderRequest`
- Broker Integration V1/V2
- E*TRADE OAuth signer and OAuth flow
- existing credential environment variables

No replacement broker contract, OAuth stack, or E*TRADE read-only adapter is created.

## Supported in V2.1
- Equity (EQ) only
- MARKET
- LIMIT
- STOP
- STOP_LIMIT
- BUY / SELL
- Preview Order
- Place Order after successful Preview
- Sandbox endpoint only

## Safety
- Production POST blocked by construction
- Sandbox network OFF by default
- explicit `--network` required
- Place is not performed by the normal build
- user-facing Sandbox CLI previews only by default
- `--place` must be explicitly added to test Sandbox Place
- no real securities or money move in E*TRADE Sandbox
- Sandbox results do not validate strategy profitability

## Official API model
E*TRADE Place Order must follow successful Preview Order and include the preview ID. Sandbox returns stored/sample responses and does not execute real transactions.
