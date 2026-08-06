[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v12001_to_v13000_portfolio_context `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "PORTFOLIO CONTEXT: READY"
Write-Host "CROSS ASSET CORRELATION: READY"
Write-Host "SIGNAL FEEDBACK: READY"
Write-Host "OFFLINE PERFORMANCE ANALYTICS: READY"
Write-Host "BROKER WRITE: OFF"
Write-Host "POSITION ALLOCATION: OFF"
Write-Host "MODEL UPDATE: OFF"
Write-Host "LIVE LEARNING: OFF"
