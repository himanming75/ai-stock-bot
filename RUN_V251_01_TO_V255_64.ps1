$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v251_01_to_v255_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
