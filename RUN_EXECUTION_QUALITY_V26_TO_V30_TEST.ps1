[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ $Python="python" }
& $Python -m unittest tools.test_execution_quality_v26_v30 -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
Write-Host "TEST: PASS"
Write-Host "V26-V30 EXECUTION QUALITY: PASS"
Write-Host "BROKER WRITE: 0"
Write-Host "ETRADE LIVE WRITE: OFF"
