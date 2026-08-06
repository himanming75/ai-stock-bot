[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v11001_to_v12000_multi_timeframe_ai `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "MULTI TIMEFRAME AI: READY"
Write-Host "MARKET REGIME 2.0: READY"
Write-Host "ADVANCED CONFIDENCE: READY"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "ORDER CANCELLATION: OFF"
Write-Host "POSITION ALLOCATION: OFF"
Write-Host "LIVE TRADING: OFF"
