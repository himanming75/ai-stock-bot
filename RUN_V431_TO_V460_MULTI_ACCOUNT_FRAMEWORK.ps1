$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v431_to_v460_multi_account_framework.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
