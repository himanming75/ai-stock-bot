$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v8001_to_v8200_etrade_certification.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
