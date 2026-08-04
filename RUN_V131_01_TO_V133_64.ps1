$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v131_01_to_v133_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
