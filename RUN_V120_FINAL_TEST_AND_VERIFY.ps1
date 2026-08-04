$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v120_final.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v120_final -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V120_FINAL.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v120_final.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V120 FINAL TEST AND VERIFY PASS"
