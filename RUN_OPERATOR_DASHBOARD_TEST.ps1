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

& $Python -m unittest tools.test_operator_dashboard -v
if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "DASHBOARD SAFETY: PASS"
Write-Host "LIVE WRITE: OFF"
