$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_op1_05_to_op1_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_daily_read_only_observation_op1_05_to_op1_08 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_OP1_05_TO_OP1_08_DAILY_OBSERVATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_daily_read_only_observation_op1_05_to_op1_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OP1.05-OP1.08 TEST AND VERIFY PASS"
