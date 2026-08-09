# Broker Integration V2.1.2 — E*TRADE Sandbox Place + Ledger + Reconciliation

Base commit: `d2967ec7`

## Non-duplication
V2.1.2 reuses:
- the existing V2.1 Preview/Place pipeline
- the existing V2 OAuth flow and signer
- the existing read-only account transport
- canonical `broker.contracts_v77_1.BrokerOrderRequest`

No replacement order engine is created.

## Added
- Explicit Sandbox Place flow
- Manual `PLACE` confirmation before Sandbox Place
- Runtime JSONL order ledger
- Account fingerprinting instead of raw accountIdKey storage
- GET Orders read-back
- Reconciliation states:
  - MATCHED
  - SAMPLE_DATA_MISMATCH
  - NOT_OBSERVED
- bilingual dashboard status

## Sandbox behavior
E*TRADE Sandbox does not execute real transactions. Valid requests receive stored/sample responses. Because stored Sandbox data may not reflect the just-submitted sample order, reconciliation explicitly distinguishes sample-data mismatch from a real execution failure.

## Safety
- Sandbox only
- Production order POST locked
- Real money/securities: none
- Profitability validation: false
- Account ID is not stored raw in the ledger
- Runtime ledger is under `runtime/` and remains outside Git
