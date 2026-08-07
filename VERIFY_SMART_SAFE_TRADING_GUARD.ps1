[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python -m unittest tools.test_smart_safe_trading_guard -v
if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "VERIFY: PASS"
Write-Host "SMART SAFETY CONTRACT: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
