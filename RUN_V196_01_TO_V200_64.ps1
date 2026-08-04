$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v196_01_to_v200_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
