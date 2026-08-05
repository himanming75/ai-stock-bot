
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Python=Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {$Python="python"}
$Old=$env:PYTHONPATH
try {
 $env:PYTHONPATH=$Root
 Write-Host "=== V451-V460 AUDIT UNIT TEST ==="
 & $Python -m unittest tools.test_v451_to_v460_audit -v
 if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
 Write-Host "=== V460.64 REPOSITORY AUDIT ==="
 & $Python (Join-Path $Root "tools\run_v451_to_v460_audit.py")
 if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
 Write-Host "=== V460.64 VERIFY ==="
 & $Python (Join-Path $Root "tools\verify_v451_to_v460_audit.py")
 exit $LASTEXITCODE
} finally {$env:PYTHONPATH=$Old}
