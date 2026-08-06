[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v13001_to_v14000_portfolio_optimizer `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "PORTFOLIO OPTIMIZER: READY"
Write-Host "SCENARIO STRESS: READY"
Write-Host "CAPITAL GUARDRAIL SIMULATION: READY"
Write-Host "BROKER WRITE: OFF"
Write-Host "POSITION ALLOCATION: OFF"
Write-Host "CAPITAL LOCK: OFF"
