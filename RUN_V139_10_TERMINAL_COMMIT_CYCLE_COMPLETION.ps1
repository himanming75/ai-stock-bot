$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V139.10 TERMINAL COMMIT AND CYCLE COMPLETION ==="
Write-Host "Local terminal commit only. No credentials, broker network, or order submission."

python tools/run_terminal_commit_cycle_completion_v139_10.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.10 TERMINAL COMMIT AND CYCLE COMPLETION COMPLETE"
