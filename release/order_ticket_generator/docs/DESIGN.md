# Execution Plan to Order Ticket Generator

This stage converts dry-run execution plans into Alpaca-compatible order
ticket payloads.

Included:

- deterministic ticket IDs
- deterministic client order IDs
- SHA256 idempotency keys
- slice-aware quantity distribution
- fractional quantity precision
- limit and market payload support
- time-in-force and extended-hours policy
- ticket-level notional validation
- JSON snapshot and append-only JSONL ledger

This stage never performs network access or order submission.
