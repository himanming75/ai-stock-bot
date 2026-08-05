
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$Old = $env:PYTHONPATH
try {
  $env:PYTHONPATH = $Root
  Write-Host "=== V444-V450 UNIT TEST ==="
  & $Python -m unittest tools.test_v444_to_v450 -v
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host "=== V450.64 INTEGRATED RUN ==="
  & $Python (Join-Path $Root "tools\run_v444_to_v450.py")
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  Write-Host "=== V450.64 VERIFY ==="
  & $Python (Join-Path $Root "tools\verify_v444_to_v450.py")
  exit $LASTEXITCODE
} finally { $env:PYTHONPATH = $Old }
