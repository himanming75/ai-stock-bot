$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v4001_to_v4200_etrade_production_routing.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
