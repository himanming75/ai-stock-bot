# Controlled Next-Order Cycle from Actual Readiness

```powershell
$env:AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_CYCLE = "YES"
$env:AI_STOCK_BOT_ACTUAL_NEXT_ORDER_CYCLE_CONFIRMATION = "EVALUATE ACTUAL NEXT ORDER READINESS AND CREATE ONE LOCAL CYCLE TOKEN ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V135_01_TO_V136_00_ACTUAL_NEXT_ORDER_CYCLE.ps1 `
  -Symbol AAPL `
  -Side BUY `
  -Quantity 1 `
  -EstimatedPrice 50 `
  -MaxQuantity 1 `
  -MaxNotional 100
```

This runner reads the saved V135 actual readiness result only. It does not access Alpaca and cannot submit an order.
