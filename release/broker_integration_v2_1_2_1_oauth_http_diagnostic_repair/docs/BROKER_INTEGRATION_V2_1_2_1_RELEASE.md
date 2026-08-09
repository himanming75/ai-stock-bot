# Broker Integration V2.1.2.1 — OAuth HTTP Diagnostic Repair

Base commit: `0ce4dc72`

Observed issue:
- E*TRADE Sandbox Place V2.1.2 stopped before Preview.
- Failure was at OAuth Request Token.
- Repeated HTTP 404 was returned.
- Existing OAuth module discarded the HTTP response body.

This repair:
- preserves OAuth HTTP status
- preserves response body
- exposes only safe response headers
- never prints Consumer Key/Secret values
- never prints OAuth token values
- leaves Preview/Place/Ledger/Reconciliation unchanged
- leaves PROD orders locked

No alternative OAuth endpoint is guessed or substituted.
The official E*TRADE documentation states that Sandbox uses the same OAuth procedure and authorization server as production.
