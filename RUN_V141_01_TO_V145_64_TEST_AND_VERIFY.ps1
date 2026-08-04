$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v141_01_to_v145_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v141_01_to_v145_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v141_01_to_v145_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V141.01-V145.64 TEST AND VERIFY PASS"
