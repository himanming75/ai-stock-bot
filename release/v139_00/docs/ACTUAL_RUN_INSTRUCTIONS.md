# Actual Saved-State Continuation

```powershell
$env:AI_STOCK_BOT_ENABLE_ACTUAL_CYCLE_CONTINUATION = "YES"
$env:AI_STOCK_BOT_ACTUAL_CYCLE_CONTINUATION_CONFIRMATION = "EVALUATE ACTUAL SAVED AUTONOMOUS CYCLE CONTINUATION LOCAL ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V138_01_TO_V139_00_ACTUAL_AUTONOMOUS_CYCLE_CONTINUATION.ps1
```

This stage uses saved results only and cannot submit an order.
