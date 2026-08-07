[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ $Python="python" }

& $Python -m unittest `
  tools.test_decision_robustness_v31_v35 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "V31-V35 DECISION ROBUSTNESS: PASS"
Write-Host "BROKER WRITE: 0"
Write-Host "ETRADE LIVE WRITE: OFF"
