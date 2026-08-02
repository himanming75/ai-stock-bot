param([string]$ClientOrderId="single-60d3c5406e5226ae71d7")
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL ALPACA PAPER TERMINAL COMPLETION COMMIT ==="
Write-Host "GET only from Alpaca. Commit writes are local ledger files only."
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_COMMIT_READ -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_COMMIT_READ=YES"}
if($env:AI_STOCK_BOT_ACTUAL_TERMINAL_COMMIT_CONFIRMATION -ne "READ ACTUAL ALPACA PAPER TERMINAL STATE AND COMMIT LOCALLY GET ONLY"){throw "Set exact terminal commit confirmation text"}

python tools/run_actual_terminal_completion_commit_v132_01_to_v133_00.py `
 --repository-root . `
 --client-order-id $ClientOrderId
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "ACTUAL TERMINAL COMPLETION COMMIT RUN COMPLETE"
