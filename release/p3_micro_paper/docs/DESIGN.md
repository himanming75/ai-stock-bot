# P3 Micro Paper Order Validation

This package creates a dedicated $5 notional equity market order for Alpaca
Paper Trading. It does not reuse the larger dry-run execution tickets.

Safety controls:

- exact Alpaca Paper endpoint only
- SPY, QQQ, or IWM only
- $1 minimum and $5 maximum notional
- market order only for fractional equity compatibility
- day time-in-force
- account must be ACTIVE
- market must be open
- asset must be tradable and fractionable
- deterministic client_order_id
- duplicate client_order_id block
- ticket SHA256-bound approval token
- 10-minute token expiry
- one-time nonce
- read-back reconciliation
- live submissions permanently zero

Installation and unit tests never submit an order.
Actual submission is a separate explicit command.
