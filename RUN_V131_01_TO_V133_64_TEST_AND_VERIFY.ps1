$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v131_01_to_v133_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v131_01_to_v133_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V131_01_TO_V133_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v131_01_to_v133_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V131.01-V133.64 TEST AND VERIFY PASS"
