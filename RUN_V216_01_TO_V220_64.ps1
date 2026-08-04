$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v216_01_to_v220_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
