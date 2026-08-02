param(
    [Parameter(Mandatory=$true)]
    [decimal]$EstimatedPrice,
    [string]$Symbol = "AAPL"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL CONTROLLED ALPACA PAPER SINGLE ORDER ==="
Write-Host "A current open order will block submission."
Write-Host "Maximum quantity: 1. Maximum estimated notional: 100 USD."
Write-Host "Live trading is forbidden."

if ($env:AI_STOCK_BOT_ENABLE_ACTUAL_CONTROLLED_PAPER_ORDER -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_CONTROLLED_PAPER_ORDER=YES"
}
if ($env:AI_STOCK_BOT_ACTUAL_CONTROLLED_PAPER_ORDER_CONFIRMATION -ne "SUBMIT EXACTLY ONE CONTROLLED ALPACA PAPER ORDER") {
    throw "Set the exact controlled Paper order confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}

python tools/run_actual_controlled_autonomous_paper_single_order_v126_01_to_v127_00.py `
    --repository-root . `
    --symbol $Symbol `
    --estimated-price $EstimatedPrice
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL CONTROLLED PAPER SINGLE ORDER RUN COMPLETE"
