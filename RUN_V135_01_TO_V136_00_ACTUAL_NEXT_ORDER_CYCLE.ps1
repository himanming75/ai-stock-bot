param(
 [string]$Symbol="AAPL",
 [string]$Side="BUY",
 [string]$Quantity="1",
 [string]$EstimatedPrice="50",
 [string]$MaxQuantity="1",
 [string]$MaxNotional="100"
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL READINESS CONTROLLED NEXT ORDER CYCLE ==="
Write-Host "Local cycle token only. No broker network and no order submission."
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_CYCLE -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_CYCLE=YES"}
if($env:AI_STOCK_BOT_ACTUAL_NEXT_ORDER_CYCLE_CONFIRMATION -ne "EVALUATE ACTUAL NEXT ORDER READINESS AND CREATE ONE LOCAL CYCLE TOKEN ONLY"){throw "Set exact next-order-cycle confirmation text"}

python tools/run_actual_controlled_autonomous_next_order_cycle_v135_01_to_v136_00.py `
 --repository-root . `
 --symbol $Symbol `
 --side $Side `
 --quantity $Quantity `
 --estimated-price $EstimatedPrice `
 --max-quantity $MaxQuantity `
 --max-notional $MaxNotional
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "ACTUAL READINESS CONTROLLED NEXT ORDER CYCLE COMPLETE"
