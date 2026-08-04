$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v306_01_to_v310_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v306_01_to_v310_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V306_01_TO_V310_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v306_01_to_v310_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V306.01-V310.64 TEST AND VERIFY PASS"
