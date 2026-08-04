$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v211_01_to_v215_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
