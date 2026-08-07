$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python -m unittest tools.test_paper_validation_ops_v1 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "TEST: PASS"
Write-Host "READ-ONLY VALIDATION OPS: PASS"
Write-Host "BROKER WRITE: 0"
