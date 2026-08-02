$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v139_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_autonomous_cycle_resume_v139_05 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_V139_05_AUTONOMOUS_CYCLE_RESUME.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_autonomous_cycle_resume_v139_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.05 TEST AND VERIFY PASS"
