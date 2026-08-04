$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools\run_v105_33_to_v105_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
