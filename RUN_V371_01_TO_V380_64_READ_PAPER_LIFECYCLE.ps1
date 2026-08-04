$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

& $Python `
  (Join-Path $Root "tools\run_v371_01_to_v380_64.py") `
  --allow-paper-network

exit $LASTEXITCODE
