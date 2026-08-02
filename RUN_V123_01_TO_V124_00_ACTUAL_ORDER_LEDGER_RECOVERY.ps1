$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL ALPACA PAPER ORDER LEDGER RECOVERY READ ==="
Write-Host "GET only. This command cannot submit, modify, or cancel orders."
if ($env:AI_STOCK_BOT_ENABLE_ACTUAL_ORDER_LEDGER_RECOVERY -ne "YES") { throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_ORDER_LEDGER_RECOVERY=YES" }
if ($env:AI_STOCK_BOT_ACTUAL_ORDER_LEDGER_RECOVERY_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER OPEN ORDERS AND RECOVER LEDGER GET ONLY") { throw "Set exact confirmation text." }
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) { throw "Set PAPER credentials." }
python tools/run_actual_order_ledger_recovery_v123_01_to_v124_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "ACTUAL ALPACA PAPER ORDER LEDGER RECOVERY READ COMPLETE"
