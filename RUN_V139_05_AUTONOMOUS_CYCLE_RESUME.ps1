$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== V139.05 AUTONOMOUS CYCLE RESUME ==="
Write-Host "Local saved-state cycle resume only. No credentials, broker network, or order submission."
python tools/run_autonomous_cycle_resume_v139_05.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.05 AUTONOMOUS CYCLE RESUME COMPLETE"
