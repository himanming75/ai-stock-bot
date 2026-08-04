$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v261_01_to_v265_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v261_01_to_v265_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V261_01_TO_V265_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v261_01_to_v265_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V261.01-V265.64 TEST AND VERIFY PASS"
