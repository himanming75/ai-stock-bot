[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) { $Python = "python" }

& $Python -m unittest tools.test_daily_session_shadow_guard_integration -v
if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Text = Get-Content .\paper_daily_session\runner.py -Raw
if($Text -notmatch "shadow_guard = DailySessionShadowGuard") {
    throw "SHADOW GUARD INTEGRATION NOT FOUND"
}

$Policy = Get-Content `
  .\release\smart_safe_trading_guard_1_0\config\guard_policy.json `
  -Raw | ConvertFrom-Json

if($Policy.mode -ne "SHADOW") { throw "MODE MUST REMAIN SHADOW" }
if($Policy.live_write_enabled -ne $false) { throw "LIVE WRITE MUST REMAIN OFF" }

Write-Host "VERIFY: PASS"
Write-Host "SHADOW MODE LOCK: PASS"
Write-Host "NON-ENFORCEMENT CONTRACT: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
