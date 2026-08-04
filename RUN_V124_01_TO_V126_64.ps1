$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v124_01_to_v126_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
