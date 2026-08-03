# V86.01-V86.08 AI Strategy Engine v2

## Included stages

- V86.01 signal input model
- V86.02 weighted signal aggregation
- V86.03 confidence scoring
- V86.04 BUY/SELL/HOLD/WATCH decision classification
- V86.05 explanation generation
- V86.06 JSON input/output integration
- V86.07 Dashboard v2 strategy payload integration
- V86.08 test, verify, release, and one-click installation

## Safety

This release is local and paper-only.

- No OpenAI or external AI API
- No external network
- No broker credentials
- No broker writes
- No order submission
- No live trading

## Run

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_01_TO_V86_08_STRATEGY_ENGINE_V2.ps1
```
