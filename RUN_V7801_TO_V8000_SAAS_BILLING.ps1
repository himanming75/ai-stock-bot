$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v7801_to_v8000_saas_billing.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
