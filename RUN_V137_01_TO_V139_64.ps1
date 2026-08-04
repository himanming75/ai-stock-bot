$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v137_01_to_v139_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
