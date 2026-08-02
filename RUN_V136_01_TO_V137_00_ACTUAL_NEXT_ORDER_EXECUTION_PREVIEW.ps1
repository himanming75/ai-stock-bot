$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL SAVED-STATE NEXT ORDER EXECUTION PREVIEW ==="
Write-Host "Local preview files only. No broker network and no order submission."
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_PREVIEW -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_PREVIEW=YES"}
if($env:AI_STOCK_BOT_ACTUAL_NEXT_ORDER_PREVIEW_CONFIRMATION -ne "BUILD ONE LOCAL NEXT ORDER SUBMISSION PREVIEW ONLY"){throw "Set exact preview confirmation text"}

python tools/run_actual_controlled_next_order_execution_preview_v136_01_to_v137_00.py `
 --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "ACTUAL SAVED-STATE NEXT ORDER EXECUTION PREVIEW COMPLETE"
