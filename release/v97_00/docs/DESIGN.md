# V96.01-V97.00 Fast Track Design

Adds read-back validation for a controlled Alpaca Paper order. It validates account, clock, order lookup by client order ID, field reconciliation, duplicate blocking, unknown-state recovery, and cancel-policy gates.

The standard pipeline remains offline. The separate actual validation runner is GET-only and submits no new order.
