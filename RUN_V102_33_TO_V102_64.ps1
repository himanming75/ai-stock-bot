$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools\run_v102_33_to_v102_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
