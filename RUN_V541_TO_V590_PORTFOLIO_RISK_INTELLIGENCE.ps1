$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python `
    .\tools\run_v541_to_v590_portfolio_risk_intelligence.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
