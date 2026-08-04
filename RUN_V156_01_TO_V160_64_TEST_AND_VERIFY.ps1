$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v156_01_to_v160_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v156_01_to_v160_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v156_01_to_v160_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V156.01-V160.64 TEST AND VERIFY PASS"
