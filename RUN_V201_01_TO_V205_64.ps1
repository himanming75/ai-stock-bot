$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v201_01_to_v205_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
