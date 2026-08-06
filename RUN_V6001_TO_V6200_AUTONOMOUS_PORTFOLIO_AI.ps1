$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v6001_to_v6200_autonomous_portfolio_ai.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
