$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v161_01_to_v165_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
