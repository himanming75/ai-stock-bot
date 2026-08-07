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

& $Python -m unittest tools.test_market_open_auto_validation -v
if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "PAPER ONLY CONTRACT: PASS"
Write-Host "MAXIMUM VALIDATION ORDERS: 1"
Write-Host "ETRADE LIVE WRITE: OFF"
