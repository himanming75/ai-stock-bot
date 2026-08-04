$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v291_01_to_v300_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
