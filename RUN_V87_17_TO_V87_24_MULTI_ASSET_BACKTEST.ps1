$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V87.17-V87.24 MULTI-ASSET BACKTEST AND BENCHMARK ==="
Write-Host "Local historical portfolio analysis only. No API, network, broker write, or order submission."

python tools\run_multi_asset_backtest_v87_17_to_v87_24.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V87.17-V87.24 COMPLETE"
