$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v127_01_to_v128_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
