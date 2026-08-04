$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v301_01_to_v305_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v301_01_to_v305_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V301_01_TO_V305_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v301_01_to_v305_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V301.01-V305.64 TEST AND VERIFY PASS"
