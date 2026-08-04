$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v246_01_to_v250_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
