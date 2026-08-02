# Actual Broker Portfolio Reconciliation

Use newly regenerated Alpaca Paper credentials only.

```powershell
$env:APCA_API_KEY_ID = "YOUR_NEW_PAPER_KEY_ID"
$env:APCA_API_SECRET_KEY = "YOUR_NEW_PAPER_SECRET"

$env:AI_STOCK_BOT_ENABLE_ACTUAL_BROKER_PORTFOLIO_READ = "YES"
$env:AI_STOCK_BOT_ACTUAL_BROKER_PORTFOLIO_CONFIRMATION = "READ ACTUAL ALPACA PAPER PORTFOLIO AND RECONCILE GET ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V124_01_TO_V125_00_ACTUAL_BROKER_PORTFOLIO_RECONCILIATION.ps1
```

This performs three GET-only reads: account, positions, and open orders. It does not submit, replace, or cancel orders.
