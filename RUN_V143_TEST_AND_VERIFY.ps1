$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v143.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_final_production_release_v143 -v
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V143_FINAL_PRODUCTION_RELEASE.ps1
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_final_production_release_v143.py
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V143 TEST AND VERIFY PASS"
