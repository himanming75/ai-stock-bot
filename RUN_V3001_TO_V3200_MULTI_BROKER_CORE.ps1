$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v3001_to_v3200_multi_broker_core.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
