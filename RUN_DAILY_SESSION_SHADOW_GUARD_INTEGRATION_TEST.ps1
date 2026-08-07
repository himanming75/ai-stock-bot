[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) { $Python = "python" }

& $Python .\tools\patch_daily_session_shadow_guard.py
if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python -m unittest `
  tools.test_daily_session_shadow_guard_integration `
  tools.test_smart_safe_trading_guard `
  tools.test_paper_autonomous_daily_session `
  -v

if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "SHADOW GUARD INTEGRATION: PASS"
Write-Host "GUARD ENFORCEMENT: OFF"
Write-Host "ORDER PATH CHANGED: NO"
Write-Host "ETRADE LIVE WRITE: OFF"
