$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH=$PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $Python .\tools\run_paper_reliability_watchdog_v2.py
exit $LASTEXITCODE
