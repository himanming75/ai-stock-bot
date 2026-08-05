$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v461_to_v490_strategy_framework.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
