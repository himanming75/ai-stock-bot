$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v271_01_to_v280_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
