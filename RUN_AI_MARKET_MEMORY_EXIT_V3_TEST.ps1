[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) { $Python = "python" }

& $Python -m unittest `
  tools.test_ai_market_memory_exit_v3 `
  -v

if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "MARKET MEMORY: PASS"
Write-Host "EXIT INTELLIGENCE: SHADOW ONLY"
Write-Host "BROKER WRITE: 0"
Write-Host "ETRADE LIVE WRITE: OFF"
