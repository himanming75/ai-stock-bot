$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v7201_to_v7400_saas_persistence.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
