$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER READ-ONLY VALIDATION ==="
Write-Host "This script sends five GET requests to the Alpaca PAPER domain."
Write-Host "It cannot submit or cancel orders because write access is disabled."

if ($env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_READ -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ALPACA_PAPER_READ=YES"
}
if ($env:AI_STOCK_BOT_ALPACA_PAPER_READ_CONFIRMATION -ne "READ MY ALPACA PAPER ACCOUNT ONLY") {
    throw "Set the exact read confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}

python tools/run_actual_alpaca_paper_read_v110_01_to_v111_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL ALPACA PAPER READ-ONLY VALIDATION PASS"
