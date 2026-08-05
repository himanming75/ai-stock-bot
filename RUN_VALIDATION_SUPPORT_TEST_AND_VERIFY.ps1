$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Project virtual environment was not found."
}
$env:PYTHONPATH = $Root

Write-Host "=== VALIDATION SUPPORT UNIT TEST ==="
& $Python -m unittest `
  tools.test_validation_support_mega_bundle -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== VALIDATION SUPPORT OFFLINE QUALIFICATION ==="
& $Python (
    Join-Path $Root `
    "tools\run_validation_support_mega_bundle.py"
)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== VALIDATION SUPPORT VERIFY ==="
& $Python (
    Join-Path $Root `
    "tools\verify_validation_support_mega_bundle.py"
)
exit $LASTEXITCODE
