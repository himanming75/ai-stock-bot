$ErrorActionPreference="Stop"; Set-Location $PSScriptRoot
python tools/install_check_v83_41_to_v83_44.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_retry_approval_supervised_reentry_v83_41_to_v83_44 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V83_41_TO_V83_44_RETRY_APPROVAL_SUPERVISED_REENTRY.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools/verify_retry_approval_supervised_reentry_v83_41_to_v83_44.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V83.41-V83.44 TEST AND VERIFY PASS"
