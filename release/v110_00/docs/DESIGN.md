# V109.01–V110.00 Alpaca Paper Broker Integration Foundation

This release adds a safe Trading API integration layer:

- Paper domain lock: `https://paper-api.alpaca.markets`
- Explicit rejection of the live trading domain
- Header authentication using paper key ID and secret
- Credential loading and redaction
- Read/write network opt-in gates
- Account, clock, positions, orders, and client-order-ID query methods
- Order payload preview
- Write-gated submit and cancel methods
- Timeout and bounded retry support
- `X-Request-ID` capture
- Broker/internal portfolio reconciliation

The normal runner performs no network request and submits no order.
