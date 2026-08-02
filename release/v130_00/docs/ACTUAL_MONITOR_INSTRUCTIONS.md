# Actual GET-only Existing Order Monitor

```powershell
$env:AI_STOCK_BOT_ENABLE_ACTUAL_LIFECYCLE_MONITOR = "YES"
$env:AI_STOCK_BOT_ACTUAL_LIFECYCLE_MONITOR_CONFIRMATION = "MONITOR ACTUAL ALPACA PAPER ORDER GET ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V129_01_TO_V130_00_ACTUAL_EXISTING_ORDER_MONITOR.ps1 `
  -MaxPolls 3 `
  -PollIntervalSeconds 5
```

Limits:

- MaxPolls: 1–20
- Poll interval: 0–300 seconds
- GET only
- No order submit, cancel, replace, or modification
