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

Write-Host "=== PHASE 3 ETRADE LIVE CANONICALIZATION ==="
Write-Host "ALPACA PAPER ONLY"
Write-Host "ETRADE LIVE ONLY"
Write-Host "ETRADE LIVE SUBMISSION: OFF"
Write-Host "OTHER BROKERS: OFF"

& $Python -m unittest `
    tools.test_phase3_etrade_live_canonicalization `
    -v

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Python .\tools\run_phase3_etrade_live_canonicalization.py

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "PHASE 3 CANONICALIZATION: COMPLETE"
Write-Host "ETRADE LIVE SCOPE LOCK: ENABLED"
Write-Host "ETRADE LIVE WRITE: OFF"
