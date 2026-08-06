$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v7001_to_v7200_saas_foundation.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
