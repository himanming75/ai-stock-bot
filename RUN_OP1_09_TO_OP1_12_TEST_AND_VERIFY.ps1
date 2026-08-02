$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_op1_09_to_op1_12.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_weekly_observation_review_op1_09_to_op1_12 -v
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_OP1_09_TO_OP1_12_WEEKLY_REVIEW.ps1
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_weekly_observation_review_op1_09_to_op1_12.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP1.09-OP1.12 TEST AND VERIFY PASS"
