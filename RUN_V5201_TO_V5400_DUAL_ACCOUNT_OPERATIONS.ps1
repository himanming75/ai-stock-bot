$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v5201_to_v5400_dual_account_operations.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
