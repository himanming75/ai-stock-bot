$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R3A DPAPI POWERSHELL COMPATIBILITY TEST ==="
& $Python -m unittest `
  tools.test_r3a_dpapi_powershell_compatibility -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R3 REGRESSION TEST ==="
& (Join-Path $Root "RUN_R3_TEST_AND_VERIFY.ps1")
exit $LASTEXITCODE
