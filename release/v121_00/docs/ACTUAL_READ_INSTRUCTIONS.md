# Actual Alpaca Paper Autonomous Read

Use Alpaca Paper credentials only.

```powershell
$env:APCA_API_KEY_ID = "YOUR_PAPER_KEY_ID"
$env:APCA_API_SECRET_KEY = "YOUR_PAPER_SECRET"
$env:AI_STOCK_BOT_ENABLE_ACTUAL_AUTONOMOUS_PAPER_READ = "YES"
$env:AI_STOCK_BOT_ACTUAL_AUTONOMOUS_PAPER_READ_CONFIRMATION = "READ ACTUAL ALPACA PAPER ACCOUNT AUTONOMOUSLY GET ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V120_01_TO_V121_00_ACTUAL_ALPACA_PAPER_READ.ps1 `
  -ClosedOrderLimit 50
```

The runner reads Account, Clock, Positions, Open Orders, and Closed Orders. It does not submit, replace, or cancel orders.
