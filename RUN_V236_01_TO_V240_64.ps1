$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v236_01_to_v240_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
