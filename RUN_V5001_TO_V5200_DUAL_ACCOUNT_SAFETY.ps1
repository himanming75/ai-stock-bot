$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v5001_to_v5200_dual_account_safety.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
