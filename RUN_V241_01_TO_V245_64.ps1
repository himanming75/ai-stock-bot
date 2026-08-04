$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v241_01_to_v245_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
