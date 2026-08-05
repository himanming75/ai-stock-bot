
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$Old = $env:PYTHONPATH
try {
  $env:PYTHONPATH = $Root
  & $Python (Join-Path $Root "tools\run_v444_to_v450.py")
  exit $LASTEXITCODE
} finally { $env:PYTHONPATH = $Old }
