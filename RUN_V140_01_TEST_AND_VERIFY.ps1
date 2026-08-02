$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v140_01.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_autonomous_runtime_supervisor_v140_01 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_V140_01_AUTONOMOUS_RUNTIME_SUPERVISOR.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_autonomous_runtime_supervisor_v140_01.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V140.01 TEST AND VERIFY PASS"
