$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v2201_to_v2400_model_governance.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
