$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER BROKER PORTFOLIO RECONCILIATION ==="
Write-Host "GET only. This command cannot submit, modify, or cancel orders."

if ($env:AI_STOCK_BOT_ENABLE_ACTUAL_BROKER_PORTFOLIO_READ -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_BROKER_PORTFOLIO_READ=YES"
}
if ($env:AI_STOCK_BOT_ACTUAL_BROKER_PORTFOLIO_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER PORTFOLIO AND RECONCILE GET ONLY") {
    throw "Set the exact broker portfolio confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}

python tools/run_actual_broker_portfolio_reconciliation_v124_01_to_v125_00.py `
    --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL ALPACA PAPER BROKER PORTFOLIO RECONCILIATION COMPLETE"
