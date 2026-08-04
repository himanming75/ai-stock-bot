$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v121_01_to_v123_64.py --real-network
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
