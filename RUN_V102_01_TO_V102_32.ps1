$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools\run_v102_01_to_v102_32.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
