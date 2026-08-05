# P2A Order Notional and Price Safety Hotfix

P2A fixes the P2 validation flaw where a user-provided reference price could be
used to approve a larger real order.

New authorization sources:

- Market notional BUY: exact order notional;
- Limit quantity: quantity multiplied by limit price;
- Market quantity: latest Alpaca trade price multiplied by quantity and a 3%
  safety buffer;
- SELL quantity: broker position quantity must be sufficient.

The `ReferencePrice` command parameter is removed from the actual order command.
P2A is a P2 defect correction and does not add a roadmap stage.
