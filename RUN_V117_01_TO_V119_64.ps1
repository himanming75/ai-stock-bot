$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v117_01_to_v119_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
