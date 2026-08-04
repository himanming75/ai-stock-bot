$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v256_01_to_v260_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v256_01_to_v260_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V256_01_TO_V260_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v256_01_to_v260_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V256.01-V260.64 TEST AND VERIFY PASS"
