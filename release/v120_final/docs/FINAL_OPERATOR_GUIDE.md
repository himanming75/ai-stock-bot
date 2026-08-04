# AI Stock Bot V120 Final Operator Guide

V120 completes the development integration for autonomous paper trading and live-ready safety architecture.

## Current permitted mode

- Autonomous paper operation
- Local read-only broker architecture
- Local order translation and validation
- Safety evaluation and reporting

## Disabled

- Live broker login
- Real external network requests
- Broker order submission
- Broker cancel/replace writes
- Fund transfers
- Automatic live execution

## Verify

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V120_FINAL_TEST_AND_VERIFY.ps1
```

## Paper operation

Continue using the V109-V110 scheduled paper operation after reviewing its task configuration.

V120 does not certify profitability. It certifies software integration and safety defaults.
