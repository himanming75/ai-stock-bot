$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== V140.01 AUTONOMOUS RUNTIME SUPERVISOR ==="
Write-Host "Local orchestration and state routing only. No credentials, broker network, or order submission."
python tools/run_autonomous_runtime_supervisor_v140_01.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V140.01 AUTONOMOUS RUNTIME SUPERVISOR COMPLETE"
