$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v111_01_to_v113_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
