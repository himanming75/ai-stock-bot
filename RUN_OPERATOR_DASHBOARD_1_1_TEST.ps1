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

& $Python -m unittest tools.test_operator_dashboard_1_1 -v
if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "OPERATION CONSOLE: PASS"
Write-Host "LIVE WRITE: OFF"
