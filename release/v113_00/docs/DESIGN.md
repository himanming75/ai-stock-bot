# V112.01–V113.00 Actual Alpaca Paper Order Validation

This release validates one known Paper order after submission.

- Uses `client_order_id`
- Polls with a bounded attempt count
- Recognizes filled, canceled, expired, rejected, and done-for-day terminal states
- Reads account and positions after polling
- Supports optional internal/broker portfolio reconciliation
- Requires a read-only Alpaca client
- Rejects any client with write network enabled
- Never submits or cancels an additional order
- Keeps Live Trading unreachable

The default pipeline uses an offline fixture. The optional actual runner performs GET requests only.
