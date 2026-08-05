# P3 Paper Cancel Validation

This validation submits one $5 Alpaca Paper limit order and cancels it.

The limit price is calculated from the latest IEX trade using a default
multiplier of 0.50. The low price is intended to keep the order open long
enough to exercise the cancel path.

Safety controls:

- exact Alpaca Paper endpoint
- SPY, QQQ, or IWM only
- $1 to $5 notional
- limit price no higher than 80% of the latest trade
- market open
- active account
- tradable and fractionable asset
- deterministic client_order_id
- duplicate client_order_id block
- one-use approval token
- nonce and plan SHA256 binding
- 10-minute expiration
- cancel request must return HTTP 204
- final broker status must be canceled
- filled quantity must remain zero
- Broker order ID and client order ID reconciliation
- Live order submissions remain zero

Installation and unit tests never submit or cancel an order.
