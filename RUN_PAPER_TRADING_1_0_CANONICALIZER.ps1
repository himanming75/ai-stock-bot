[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if(Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}
else {
    $Python = "python"
}

Write-Host "=== PAPER TRADING 1.0 CANONICALIZER ==="
Write-Host "EXISTING CODE ONLY"
Write-Host "NEW FEATURE DEVELOPMENT: FROZEN"
Write-Host "ACTUAL PAPER ORDERS TODAY: 0"
Write-Host "LIVE SUBMISSION: OFF"

& $Python -m unittest `
    tools.test_paper_trading_1_0_canonicalizer `
    -v

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Python .\tools\run_paper_trading_1_0_canonicalizer.py

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "CANONICALIZER: COMPLETE"
Write-Host "ACTUAL MARKET-DAY VALIDATION: NOT RUN"
Write-Host "PAPER ORDERS SUBMITTED: 0"
Write-Host "LIVE ORDERS SUBMITTED: 0"
