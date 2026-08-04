# V321.01-V330.64 Real Paper Long-Run Qualification

This stage qualifies the V311.01-V320.64 Alpaca Paper read-only collector over a long-running session.

## Safety invariants

- Alpaca Paper endpoint only
- Paper order submission disabled
- Live order submission disabled
- Broker writes disabled
- Maximum new orders per day: 0
- Existing account, position, and order data are observed only

## Main capabilities

- 30-second long-run observation cycles
- Atomic checkpoint persistence
- Safe Ctrl+C interruption without traceback
- Exponential retry delay after transient exceptions
- Consecutive error limit
- JSONL corruption detection
- Timestamp continuity and excessive-gap analysis
- Duplicate cycle-record detection
- Success-ratio and observation-duration qualification
- Market-close automatic stop after an open session
- Qualification report and Web Controller status functions

## Enable

```powershell
powershell -ExecutionPolicy Bypass -File .\ENABLE_V321_REAL_PAPER_LONG_RUN_QUALIFICATION.ps1
```

Enter `ENABLE_REAL_PAPER_LONG_RUN_QUALIFICATION`.

## Run session

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V321_01_TO_V330_64_LONG_RUN_SESSION.ps1
```

The default target is at least 120 successful cycles and 60 minutes with a success ratio of 98% or higher. A user interruption is recorded as `USER_INTERRUPTED_SAFE`, with a summary written before exit.

## Analyze at any time

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V321_01_TO_V330_64_ANALYZE.ps1
```

Possible states:

- `REAL_PAPER_LONG_RUN_READY_BLOCKED`
- `REAL_PAPER_LONG_RUN_QUALIFICATION_PENDING`
- `REAL_PAPER_LONG_RUN_QUALIFIED`

## Test and verify

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_V321_01_TO_V330_64_TEST_AND_VERIFY.ps1
```
