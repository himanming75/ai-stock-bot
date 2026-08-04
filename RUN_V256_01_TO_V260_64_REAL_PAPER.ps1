$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v256_01_to_v260_64.py --allow-paper-network
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
