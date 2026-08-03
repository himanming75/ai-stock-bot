$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\run_v99_01_to_v99_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
