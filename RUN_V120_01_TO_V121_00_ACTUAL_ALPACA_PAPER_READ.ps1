param(
    [int]$ClosedOrderLimit = 50
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER AUTONOMOUS GET-ONLY READ ==="
Write-Host "This runner uses GET only. It cannot submit, modify, or cancel orders."

if ($env:AI_STOCK_BOT_ENABLE_ACTUAL_AUTONOMOUS_PAPER_READ -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_AUTONOMOUS_PAPER_READ=YES"
}
if ($env:AI_STOCK_BOT_ACTUAL_AUTONOMOUS_PAPER_READ_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER ACCOUNT AUTONOMOUSLY GET ONLY") {
    throw "Set the exact autonomous Paper read confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}
if ($ClosedOrderLimit -lt 1 -or $ClosedOrderLimit -gt 500) {
    throw "ClosedOrderLimit must be between 1 and 500."
}

python tools/run_actual_autonomous_paper_read_v120_01_to_v121_00.py `
    --repository-root . `
    --closed-order-limit $ClosedOrderLimit
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL ALPACA PAPER AUTONOMOUS READ COMPLETE"
