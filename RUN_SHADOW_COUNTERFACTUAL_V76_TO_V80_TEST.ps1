[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_shadow_counterfactual_v76_v80 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "V76-V80 COUNTERFACTUAL: PASS"
Write-Host "BROKER WRITE: 0"
Write-Host "ETRADE LIVE WRITE: OFF"
