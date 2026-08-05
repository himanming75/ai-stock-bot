$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R4 UNIT TEST ==="
& $Python -m unittest tools.test_r4_configuration_profiles -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R4 PROFILE CATALOG ==="
& $Python (Join-Path $Root "tools\run_r4_profile_catalog.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R4 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_r4_configuration_profiles.py")
exit $LASTEXITCODE
