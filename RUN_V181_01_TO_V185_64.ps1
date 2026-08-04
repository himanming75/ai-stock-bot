$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v181_01_to_v185_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
