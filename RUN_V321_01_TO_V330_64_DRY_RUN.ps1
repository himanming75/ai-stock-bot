$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
& $Python (Join-Path $PSScriptRoot "tools\run_v321_01_to_v330_64.py") --no-sleep
exit $LASTEXITCODE
