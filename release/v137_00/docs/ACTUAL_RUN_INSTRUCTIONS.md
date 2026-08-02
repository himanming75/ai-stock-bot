# Actual Saved-State Preview

```powershell
$env:AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_PREVIEW = "YES"
$env:AI_STOCK_BOT_ACTUAL_NEXT_ORDER_PREVIEW_CONFIRMATION = "BUILD ONE LOCAL NEXT ORDER SUBMISSION PREVIEW ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V136_01_TO_V137_00_ACTUAL_NEXT_ORDER_EXECUTION_PREVIEW.ps1
```

This command reads saved V135/V136 local results only. It does not connect to Alpaca and cannot submit an order.
