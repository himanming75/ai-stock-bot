$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v7601_to_v7800_saas_operations.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
