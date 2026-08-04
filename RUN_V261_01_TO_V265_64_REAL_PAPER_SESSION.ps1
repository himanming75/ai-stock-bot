$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v261_01_to_v265_64.py --allow-paper-network
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
