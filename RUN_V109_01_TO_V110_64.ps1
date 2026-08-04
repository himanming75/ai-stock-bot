$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v109_01_to_v110_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
