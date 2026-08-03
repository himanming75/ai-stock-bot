$ErrorActionPreference="Stop"; Set-Location $PSScriptRoot
python tools/install_check_v83_45_to_v83_48.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_reentry_execution_guard_audit_v83_45_to_v83_48 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V83_45_TO_V83_48_REENTRY_EXECUTION_GUARD_AUDIT.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_reentry_execution_guard_audit_v83_45_to_v83_48.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.45-V83.48 TEST AND VERIFY PASS"
