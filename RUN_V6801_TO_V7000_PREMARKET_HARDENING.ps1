$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v6801_to_v7000_premarket_hardening.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
