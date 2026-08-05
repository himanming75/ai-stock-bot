$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v5401_to_v5600_dual_account_final.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
