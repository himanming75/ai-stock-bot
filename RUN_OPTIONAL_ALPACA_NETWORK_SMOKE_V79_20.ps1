$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "This optional command can execute ONE read-only AAPL historical data request."
Write-Host "It requires ALPACA_ENABLE_NETWORK_SMOKE=YES and Alpaca credentials."
python tools/run_optional_live_network_smoke_v79_20.py
exit $LASTEXITCODE
