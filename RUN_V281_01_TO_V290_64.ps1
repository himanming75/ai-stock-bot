$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v281_01_to_v290_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
