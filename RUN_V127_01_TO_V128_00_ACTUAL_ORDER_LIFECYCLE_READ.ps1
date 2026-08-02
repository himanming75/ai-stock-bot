param([string]$ClientOrderId="single-60d3c5406e5226ae71d7")
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL ALPACA PAPER ORDER LIFECYCLE GET-ONLY READ ==="
Write-Host "No order submission, modification, or cancellation is possible."
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_ORDER_LIFECYCLE_READ -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_ORDER_LIFECYCLE_READ=YES"}
if($env:AI_STOCK_BOT_ACTUAL_ORDER_LIFECYCLE_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER ORDER LIFECYCLE GET ONLY"){throw "Set exact lifecycle confirmation text"}
python tools/run_actual_existing_paper_order_lifecycle_v127_01_to_v128_00.py --repository-root . --client-order-id $ClientOrderId
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "ACTUAL PAPER ORDER LIFECYCLE READ COMPLETE"
