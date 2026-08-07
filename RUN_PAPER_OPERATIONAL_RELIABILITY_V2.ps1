$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH=$PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python .\tools\run_paper_operational_reliability_v2.py --repository-root $PSScriptRoot
exit $LASTEXITCODE
