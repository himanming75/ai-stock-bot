# V97.01-V97.32 Paper Broker Adapter & Safe API Boundary

## Included

- V97.01-V97.08 broker interface, mock adapter and factory
- V97.09-V97.16 Alpaca and IBKR read-only adapter shells
- V97.17-V97.24 account, position, order-plan and fill translators
- V97.25-V97.32 safe API boundary, capability detection, health checks, audit ledger, certificate, tests and release

All broker write methods raise `PermissionError`. Credentials and external network access remain disabled.
