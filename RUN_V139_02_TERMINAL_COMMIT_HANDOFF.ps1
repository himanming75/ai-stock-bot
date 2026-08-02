$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V139.02 TERMINAL COMMIT HANDOFF ==="
Write-Host "Local saved-state handoff only. No credentials, broker network, or order submission."

python tools/run_terminal_commit_handoff_v139_02.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.02 TERMINAL COMMIT HANDOFF COMPLETE"
