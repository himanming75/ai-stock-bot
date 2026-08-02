# Actual GET-only Fill Reconciliation

```powershell
$env:AI_STOCK_BOT_ENABLE_ACTUAL_FILL_RECONCILIATION_READ = "YES"
$env:AI_STOCK_BOT_ACTUAL_FILL_RECONCILIATION_CONFIRMATION = "READ ACTUAL ALPACA PAPER ORDER POSITION ACCOUNT GET ONLY"

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V128_01_TO_V129_00_ACTUAL_FILL_RECONCILIATION_READ.ps1
```

Expected while the existing order remains accepted:

```text
state = WAITING_ACTIVE_ORDER
new_order_allowed = false
write_requests_executed = 0
```
