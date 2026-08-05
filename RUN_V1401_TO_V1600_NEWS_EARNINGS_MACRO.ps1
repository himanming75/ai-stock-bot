$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v1401_to_v1600_news_earnings_macro.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
