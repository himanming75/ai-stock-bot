$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\run_v186_01_to_v190_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
