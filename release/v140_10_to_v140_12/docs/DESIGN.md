# V140.10-V140.12 Alpaca Paper Integration

Integrated stages:

- V140.10 Paper Broker Read
- V140.11 Paper Submission with client-order-id idempotency
- V140.12 Broker Reconciliation

Safety defaults:

- Local snapshot mode
- Network disabled
- Submission disabled
- Live endpoint blocked
- Live orders fixed at zero

Actual Paper mode requires the exact Paper endpoint, Paper credentials in environment variables, explicit network and submission switches, and the exact approval phrase:

`APPROVE V140 PAPER ORDER SUBMISSION`
