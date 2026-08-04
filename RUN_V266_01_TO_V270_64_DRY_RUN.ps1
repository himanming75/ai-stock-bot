$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v266_01_to_v270_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
