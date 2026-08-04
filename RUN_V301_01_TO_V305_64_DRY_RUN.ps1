$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v301_01_to_v305_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
