$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER OPEN ORDER IDENTITY READ ==="
Write-Host "GET only. This command cannot submit, modify, or cancel orders."

if ($env:AI_STOCK_BOT_ENABLE_ACTUAL_OPEN_ORDER_IDENTITY_READ -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_OPEN_ORDER_IDENTITY_READ=YES"
}
if ($env:AI_STOCK_BOT_ACTUAL_OPEN_ORDER_IDENTITY_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER OPEN ORDER IDENTITIES GET ONLY") {
    throw "Set the exact open-order identity confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}

python tools/run_actual_open_order_identity_read_v122_01_to_v123_00.py `
    --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL ALPACA PAPER OPEN ORDER IDENTITY READ COMPLETE"
