$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v306_01_to_v310_64.py --allow-paper-network
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
