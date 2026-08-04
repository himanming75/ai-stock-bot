$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v101_01_to_v101_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
