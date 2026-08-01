$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "OPTIONAL NETWORK RUNNER - READ-ONLY ALPACA MARKET DATA"
python tools/run_actual_alpaca_market_data_v102_01_to_v103_00.py @args
exit $LASTEXITCODE
