
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v83_13_to_v83_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_supervised_automation_runner_v83_13_to_v83_16 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V83_13_TO_V83_16_SUPERVISED_RUNNER.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_supervised_automation_runner_v83_13_to_v83_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.13-V83.16 TEST AND VERIFY PASS"
