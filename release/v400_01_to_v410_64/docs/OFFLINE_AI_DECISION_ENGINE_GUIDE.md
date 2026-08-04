# V400.01–V410.64 Offline AI Decision Engine

## Purpose

Create deterministic BUY/SELL/HOLD analytical decisions from local JSON features.
This stage does not connect to a broker and cannot submit an order.

## Inputs

- close
- fast and slow moving averages
- RSI
- ATR percentage
- relative volume
- broad-market trend score
- optional offline news score

## Outputs

- analytical action;
- confidence;
- market regime;
- normalized score;
- risk level;
- reasons;
- self-review findings.

## Safety

`BUY` and `SELL` are labels only. `order_submission_allowed` is always false.
Paper and Live order counts remain zero.

## Run

```powershell
& .\RUN_V400_01_TO_V410_64_OFFLINE_AI_DECISION.ps1
```

## Test and verify

```powershell
& .\RUN_V400_01_TO_V410_64_TEST_AND_VERIFY.ps1
```
