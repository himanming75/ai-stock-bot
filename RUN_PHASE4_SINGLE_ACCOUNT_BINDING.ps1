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

Write-Host "=== PHASE 4 SINGLE ACCOUNT BINDING ==="
Write-Host "ALPACA PAPER ACCOUNT COUNT: 1"
Write-Host "ETRADE LIVE ACCOUNT COUNT: 1"
Write-Host "MULTI ACCOUNT: OFF"
Write-Host "ACCOUNT SWITCH: OFF"
Write-Host "LIVE SUBMISSION: OFF"

& $Python -m unittest `
    tools.test_phase4_single_account_binding `
    -v

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Python .\tools\run_phase4_single_account_binding.py

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "PHASE 4 CANONICALIZATION: COMPLETE"
Write-Host "SINGLE ACCOUNT SCOPE LOCK: ENABLED"
Write-Host "MULTI ACCOUNT: OFF"
