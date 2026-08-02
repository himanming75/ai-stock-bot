# Actual Open Order Identity Read

Use newly regenerated Alpaca Paper credentials only.

```powershell
$env:APCA_API_KEY_ID = "YOUR_NEW_PAPER_KEY_ID"
$env:APCA_API_SECRET_KEY = "YOUR_NEW_PAPER_SECRET"

$env:AI_STOCK_BOT_ENABLE_ACTUAL_OPEN_ORDER_IDENTITY_READ = "YES"
$env:AI_STOCK_BOT_ACTUAL_OPEN_ORDER_IDENTITY_CONFIRMATION = "READ ACTUAL ALPACA PAPER OPEN ORDER IDENTITIES GET ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V122_01_TO_V123_00_ACTUAL_OPEN_ORDER_IDENTITY_READ.ps1
```

The command performs only an open-orders GET request. It cannot submit, replace, or cancel orders.
