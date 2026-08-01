# Actual Alpaca Paper Single-Order Instructions

This optional command submits one order to your **Paper** account.

Use Paper credentials only. In the current PowerShell window:

```powershell
$env:APCA_API_KEY_ID = "YOUR_PAPER_KEY_ID"
$env:APCA_API_SECRET_KEY = "YOUR_PAPER_SECRET"
$env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_SINGLE_ORDER = "YES"
$env:AI_STOCK_BOT_ALPACA_PAPER_ORDER_CONFIRMATION = "SUBMIT ONE ALPACA PAPER ORDER ONLY"

powershell -ExecutionPolicy Bypass -File .\RUN_V111_01_TO_V112_00_ACTUAL_ALPACA_PAPER_SINGLE_ORDER.ps1 `
  -Symbol AAPL `
  -Side buy `
  -Quantity 1 `
  -ReferencePrice 50
```

The reference price is used only to enforce the $100 safety ceiling. The submitted order is a market/day Paper order.

Do not commit API credentials or actual-order output containing broker identifiers.
