$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python `
    .\tools\run_v1001_to_v1200_ai_market_intelligence.py `
    --minimum-bars 20
if($LASTEXITCODE -ne 0){
    Write-Host "AI MARKET INTELLIGENCE REQUIRES MORE OR VALID BARS"
    exit $LASTEXITCODE
}
