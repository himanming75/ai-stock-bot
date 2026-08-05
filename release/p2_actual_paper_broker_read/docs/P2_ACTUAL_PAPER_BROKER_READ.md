# P2 Actual Paper Broker Read Validation

P2 performs four authenticated GET requests against the Alpaca Paper Trading
endpoint:

- `/v2/account`
- `/v2/positions`
- `/v2/orders?status=open&direction=asc`
- `/v2/clock`

The existing `ReadOnlyHttpClient` accepts GET only. The execution script also
requires the operator to supply `-ConfirmReadOnly` before network access is
enabled for the current process.

P2 does not submit, replace, modify, or cancel orders. It does not change the
portfolio and does not access the live Alpaca endpoint.

A passing P2 result creates a certificate that allows development of P3, but
P3 Paper order submission remains blocked until it is separately reviewed and
explicitly executed.
