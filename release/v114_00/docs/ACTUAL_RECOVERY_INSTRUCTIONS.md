# Recover One Existing Alpaca Paper Order

Use this only for an order that was already submitted to the Alpaca Paper account.

```powershell
$env:APCA_API_KEY_ID = "YOUR_PAPER_KEY_ID"
$env:APCA_API_SECRET_KEY = "YOUR_PAPER_SECRET"
$env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_RECOVERY = "YES"
$env:AI_STOCK_BOT_ALPACA_PAPER_ORDER_RECOVERY_CONFIRMATION = "RECOVER ONE EXISTING ALPACA PAPER ORDER READ ONLY"

powershell -ExecutionPolicy Bypass -File .\RUN_V113_01_TO_V114_00_ACTUAL_ALPACA_PAPER_ORDER_RECOVERY.ps1 `
  -ClientOrderId "BOT-PAPER-ONE-YYYYMMDDHHMMSS" `
  -Symbol AAPL `
  -Side buy `
  -Quantity 1 `
  -LastFilledQuantity 0 `
  -LastStatus accepted
```

The script records a local checkpoint and performs a GET-only lookup. It does not submit or cancel an order.
