$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v176_01_to_v180_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
