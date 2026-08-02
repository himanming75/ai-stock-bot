# V122.01–V123.00 Autonomous Paper Order Identity Reconciliation

The identity reconciler classifies each open order as:

- BOT: client_order_id begins with an approved bot prefix
- EXTERNAL: client_order_id is present but does not use a bot prefix
- UNKNOWN: client_order_id is missing

A BOT order must also exist in the internal order ledger by client order ID or broker order ID. Bot-prefixed orders missing from the ledger remain blocking.

Blocking conditions:

- external/manual order
- unknown ownership
- unrecognized bot-prefixed order
- unapproved symbol
- unsupported side

The standard demo validates the external-order Safe Mode path. The optional actual runner performs one GET-only open-order read and writes a redacted identity report. No order is submitted, changed, or canceled.
