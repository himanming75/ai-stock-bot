param(
 [int]$MaxPositions=3,
 [string]$MaxTotalMarketValue="1000",
 [string]$RiskApproved="YES"
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL ALPACA PAPER NEXT ORDER READINESS ==="
Write-Host "GET only. This command cannot submit, modify, replace, or cancel orders."
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_READINESS -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_READINESS=YES"}
if($env:AI_STOCK_BOT_ACTUAL_NEXT_ORDER_READINESS_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER ACCOUNT FOR NEXT ORDER READINESS GET ONLY"){throw "Set exact readiness confirmation text"}

python tools/run_actual_autonomous_next_order_readiness_v134_01_to_v135_00.py `
 --repository-root . `
 --max-positions $MaxPositions `
 --max-total-market-value $MaxTotalMarketValue `
 --risk-approved $RiskApproved
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "ACTUAL NEXT ORDER READINESS COMPLETE"
