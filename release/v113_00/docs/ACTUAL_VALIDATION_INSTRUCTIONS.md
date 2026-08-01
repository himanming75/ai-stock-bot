# Validate an Existing Alpaca Paper Order

Run this only after a controlled Paper order has already been submitted.

```powershell
$env:APCA_API_KEY_ID = "YOUR_PAPER_KEY_ID"
$env:APCA_API_SECRET_KEY = "YOUR_PAPER_SECRET"
$env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_VALIDATION = "YES"
$env:AI_STOCK_BOT_ALPACA_PAPER_ORDER_VALIDATION_CONFIRMATION = "VALIDATE ONE EXISTING ALPACA PAPER ORDER ONLY"

powershell -ExecutionPolicy Bypass -File .\RUN_V112_01_TO_V113_00_VALIDATE_EXISTING_ALPACA_PAPER_ORDER.ps1 `
  -ClientOrderId "BOT-PAPER-ONE-YYYYMMDDHHMMSS"
```

This validation script sends GET requests only. It does not submit or cancel an order.
