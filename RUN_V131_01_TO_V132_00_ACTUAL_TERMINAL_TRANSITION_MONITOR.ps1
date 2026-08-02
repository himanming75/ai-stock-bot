param(
 [string]$ClientOrderId="single-60d3c5406e5226ae71d7",
 [int]$MaxPolls=3,
 [double]$PollIntervalSeconds=5
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL ALPACA PAPER TERMINAL TRANSITION MONITOR ==="
Write-Host "GET only. No submit, replace, modify, or cancel."
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_TRANSITION_MONITOR -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_TRANSITION_MONITOR=YES"}
if($env:AI_STOCK_BOT_ACTUAL_TERMINAL_TRANSITION_CONFIRMATION -ne "MONITOR ACTUAL ALPACA PAPER ORDER AND EVALUATE TERMINAL GET ONLY"){throw "Set exact confirmation text"}
python tools/run_actual_continued_order_monitor_terminal_transition_v131_01_to_v132_00.py `
 --repository-root . `
 --client-order-id $ClientOrderId `
 --max-polls $MaxPolls `
 --poll-interval-seconds $PollIntervalSeconds
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "ACTUAL TERMINAL TRANSITION MONITOR COMPLETE"
