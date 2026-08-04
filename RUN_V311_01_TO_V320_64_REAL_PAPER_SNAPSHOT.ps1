$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v311_01_to_v320_64.py --allow-paper-network
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
