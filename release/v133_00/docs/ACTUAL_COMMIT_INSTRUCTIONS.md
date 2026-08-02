# Actual GET-only terminal completion commit

```powershell
$env:AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_COMMIT_READ = "YES"
$env:AI_STOCK_BOT_ACTUAL_TERMINAL_COMMIT_CONFIRMATION = "READ ACTUAL ALPACA PAPER TERMINAL STATE AND COMMIT LOCALLY GET ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V132_01_TO_V133_00_ACTUAL_TERMINAL_COMPLETION_COMMIT.ps1
```

If the order remains ACCEPTED, the expected state is `CONTINUE_TRACKING` and no local terminal ledger is written.
