$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v94_33_to_v94_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
