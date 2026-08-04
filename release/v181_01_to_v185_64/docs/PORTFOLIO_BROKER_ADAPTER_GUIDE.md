# V181-V185 Portfolio & Broker Adapter Foundation

This stage provides a common read-only interface for multiple brokers and accounts.

Included:

- account snapshot model
- position snapshot model
- read-only BrokerAdapter base class
- fixture adapters for Alpaca Paper and Alpaca Live Read-Only
- disabled E*TRADE foundation entry
- multi-account registry
- consolidated portfolio totals
- cash, gross exposure and net exposure
- symbol, strategy and broker allocation
- portfolio risk gate
- web Portfolio API

No adapter supports order submission in this release.
