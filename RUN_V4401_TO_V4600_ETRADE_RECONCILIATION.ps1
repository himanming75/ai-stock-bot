$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v4401_to_v4600_etrade_reconciliation.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
