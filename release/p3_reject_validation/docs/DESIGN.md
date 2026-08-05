# P3 Paper Reject Validation

This validation intentionally sends an invalid Alpaca Paper order containing
both `qty` and `notional`. Those fields are mutually exclusive, so the broker
must reject the request and create no order.

PASS requires:

- exact Paper endpoint
- active Paper account
- one-use SHA256-bound nonce token
- HTTP 400 or 422 rejection
- lookup by client_order_id finds no broker order
- actual submitted Paper orders remain zero
- actual Live orders remain zero

Installation and tests perform no network request.
