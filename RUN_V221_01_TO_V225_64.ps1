$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v221_01_to_v225_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
