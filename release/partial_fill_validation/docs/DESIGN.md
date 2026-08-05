# P3 Partial Fill Handling Validation

A genuine partial fill depends on exchange liquidity and cannot be guaranteed
on demand. This stage therefore separates two requirements:

1. Deterministic validation of partial-fill accounting and reconciliation.
2. Opportunistic read-only observation of actual Alpaca Paper orders.

For a partially filled order the engine verifies:

- requested quantity
- filled quantity
- remaining quantity
- fill ratio
- average fill price
- filled notional
- matching position quantity
- invalid overfill detection
- missing average-price detection

The actual monitor repeatedly scans Paper orders. If a real
`partially_filled` state appears, it stores per-cycle JSON and an append-only
JSONL ledger. If no partial fill appears, the handler can still PASS while the
summary clearly reports that no real partial fill was observed in the window.

This stage is read-only and submits no new order.
