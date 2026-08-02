param(
 [string]$ClientOrderId="single-60d3c5406e5226ae71d7",
 [int]$MaxPolls=3,
 [double]$PollIntervalSeconds=5
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL ALPACA PAPER TERMINAL MONITOR + LOCAL COMMIT ==="
Write-Host "GET only from Alpaca. All commit writes are local files."
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_MONITOR_COMMIT -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_MONITOR_COMMIT=YES"}
if($env:AI_STOCK_BOT_ACTUAL_TERMINAL_MONITOR_COMMIT_CONFIRMATION -ne "MONITOR ACTUAL ALPACA PAPER ORDER AND COMMIT TERMINAL LOCALLY GET ONLY"){throw "Set exact confirmation text"}
python tools/run_actual_terminal_monitor_commit_orchestrator_v133_01_to_v134_00.py `
 --repository-root . `
 --client-order-id $ClientOrderId `
 --max-polls $MaxPolls `
 --poll-interval-seconds $PollIntervalSeconds
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "ACTUAL TERMINAL MONITOR COMMIT RUN COMPLETE"
