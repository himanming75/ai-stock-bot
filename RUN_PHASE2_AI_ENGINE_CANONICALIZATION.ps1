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

Write-Host "=== PHASE 2 AI ENGINE CANONICALIZATION ==="
Write-Host "EXISTING AI CODE ONLY"
Write-Host "NEW AI FEATURES: FROZEN"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"

& $Python -m unittest `
    tools.test_phase2_ai_engine_canonicalization `
    -v

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $Python .\tools\run_phase2_ai_engine_canonicalization.py

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "PHASE 2 CANONICALIZATION: COMPLETE"
Write-Host "AI SCOPE LOCK: ENABLED"
Write-Host "NEW AI FEATURE DEVELOPMENT: OFF"
