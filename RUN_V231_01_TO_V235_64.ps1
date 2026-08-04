$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v231_01_to_v235_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
