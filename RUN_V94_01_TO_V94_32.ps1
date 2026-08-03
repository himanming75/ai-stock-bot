$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v94_01_to_v94_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
