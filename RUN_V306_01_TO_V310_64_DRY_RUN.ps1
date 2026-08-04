$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v306_01_to_v310_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
