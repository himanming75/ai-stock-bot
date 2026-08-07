$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH=$PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python -m unittest tools.test_paper_operational_reliability_v2 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "TEST: PASS"
