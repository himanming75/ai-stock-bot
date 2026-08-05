$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v4801_to_v5000_etrade_operational_readiness.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
