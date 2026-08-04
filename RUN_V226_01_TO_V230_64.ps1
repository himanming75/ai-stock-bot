$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v226_01_to_v230_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
