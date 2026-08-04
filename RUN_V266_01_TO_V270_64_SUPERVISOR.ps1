$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v266_01_to_v270_64.py --execute-child
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
