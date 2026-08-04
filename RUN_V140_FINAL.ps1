$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v140_final.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
