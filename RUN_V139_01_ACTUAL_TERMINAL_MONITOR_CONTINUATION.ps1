$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== V139.01 ACTUAL SAVED-STATE TERMINAL MONITOR CONTINUATION ==="
Write-Host "Local saved-state inspection only. No credentials, broker network, or order submission."
python tools/run_actual_terminal_monitor_continuation_v139_01.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.01 ACTUAL TERMINAL MONITOR CONTINUATION COMPLETE"
