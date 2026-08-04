$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v106_33_to_v108_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
