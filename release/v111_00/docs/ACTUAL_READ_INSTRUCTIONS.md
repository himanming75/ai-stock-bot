# Actual Alpaca Paper Read-Only Instructions

Use only Alpaca Paper credentials.

In the current PowerShell window:

```powershell
$env:APCA_API_KEY_ID = "YOUR_PAPER_KEY_ID"
$env:APCA_API_SECRET_KEY = "YOUR_PAPER_SECRET"
$env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_READ = "YES"
$env:AI_STOCK_BOT_ALPACA_PAPER_READ_CONFIRMATION = "READ MY ALPACA PAPER ACCOUNT ONLY"

powershell -ExecutionPolicy Bypass -File .\RUN_V110_01_TO_V111_00_ACTUAL_ALPACA_PAPER_READ.ps1
```

The result is written under:

`release\v111_00\actual_read\actual_alpaca_paper_read_result.json`

Do not commit credentials. Environment variables are not written to the report.
