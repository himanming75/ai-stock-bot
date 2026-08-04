$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v129_01_to_v130_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
