$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v2001_to_v2200_model_validation.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
