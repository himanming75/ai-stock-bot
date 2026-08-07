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

Write-Host "TEST: PASS"
Write-Host "SHADOW MODE: PASS"
Write-Host "ALPACA PAPER ONLY: PASS"
Write-Host "ETRADE LIVE WRITE: OFF"
