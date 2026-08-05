# Paper Order Submission Gate and Reconciliation

The installation and test workflow never submits an order.

Actual Paper submission requires all of the following:

- Alpaca Paper endpoint exactly
- Paper credentials loaded
- market open
- one-use approval token
- matching ticket snapshot SHA256
- matching nonce
- token not expired
- token not previously used
- symbol allowlist
- limit order
- maximum one order
- maximum $100 notional
- maximum quantity 1
- no duplicate open client_order_id

After submission, the service reads the order back by client_order_id and
records reconciliation evidence.

Live endpoint and live order submission remain blocked.
