$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v166_01_to_v170_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
