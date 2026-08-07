[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_market_regime_v66_v70 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "V66-V70 MARKET REGIME: PASS"
Write-Host "BROKER WRITE: 0"
Write-Host "ETRADE LIVE WRITE: OFF"
