# V83.77-V83.80 Multi-Day Paper Validation

## Scope

- V83.77 validation policy and source eligibility
- V83.78 one-record-per-calendar-date ledger
- V83.79 minimum-day aggregation
- V83.80 dashboard state and verification

## Safety Boundary

This release is local and paper-only.

- No broker credentials
- No external network
- No broker writes
- No order submission
- No live trading
- No continuous loop
- No Windows Task Scheduler
- No automatic broker execution

## Normal Execution

Run once per distinct validation date:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_77_TO_V83_80_MULTI_DAY_PAPER_VALIDATION.ps1
```

For deterministic local testing, specify a date:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_77_TO_V83_80_MULTI_DAY_PAPER_VALIDATION.ps1 `
  -ValidationDate "2026-08-04" `
  -ObservedAt "2026-08-04T16:00:00+00:00"
```

A duplicate date does not add another validation day.

After at least three unique dates, the next phase becomes
`V83_81_PAPER_STABILITY_CERTIFICATION`.
