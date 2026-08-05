$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v4201_to_v4400_etrade_unified_portfolio.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
