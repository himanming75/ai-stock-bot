# Actual Controlled Paper Single Order

The current account contains one recovered open order. The expected result is `EXISTING_ORDER_WAIT`; no new order should be submitted.

Use newly regenerated Paper credentials.

```powershell
$env:AI_STOCK_BOT_ENABLE_ACTUAL_CONTROLLED_PAPER_ORDER = "YES"
$env:AI_STOCK_BOT_ACTUAL_CONTROLLED_PAPER_ORDER_CONFIRMATION = "SUBMIT EXACTLY ONE CONTROLLED ALPACA PAPER ORDER"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V126_01_TO_V127_00_ACTUAL_CONTROLLED_PAPER_SINGLE_ORDER.ps1 `
  -Symbol AAPL `
  -EstimatedPrice 50
```

The estimated price is used only for the $100 safety cap. The submitted order type, when all gates pass, is MARKET/DAY for exactly one share.

Do not run this command after the existing order disappears without first reviewing the account state: at that point it can submit one real Alpaca Paper order.
