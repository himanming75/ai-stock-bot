$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v7401_to_v7600_saas_security.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
