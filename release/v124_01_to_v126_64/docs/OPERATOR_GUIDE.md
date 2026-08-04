# V124-V126 Operator Guide

Default installation is offline and submits no order.

## Real Paper Shadow

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V124_TO_V126_REAL_SHADOW.ps1
```

This reads the Alpaca Paper account and market data, creates Paper plans and Live Shadow records, but submits no order.

## Automated Paper cycle

First review `continuous_paper_shadow_policy.json` and set:

```json
"automated_paper_submission_enabled": true
```

Then run:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V124_TO_V126_AUTOMATED_PAPER_CYCLE.ps1
```

Type `AUTO PAPER`.

The script only uses Alpaca Paper credentials. Live orders remain disabled.
