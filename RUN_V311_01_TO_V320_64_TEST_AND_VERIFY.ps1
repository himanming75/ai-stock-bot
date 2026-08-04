$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v311_01_to_v320_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v311_01_to_v320_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V311_01_TO_V320_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v311_01_to_v320_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V311.01-V320.64 TEST AND VERIFY PASS"
