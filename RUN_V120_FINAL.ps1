$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v120_final.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
