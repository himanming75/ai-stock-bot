param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V85.01-V85.08 ONE-CLICK INSTALL ==="
Write-Host "Source:  $PSScriptRoot"
Write-Host "Project: $ProjectPath"

if (-not (Test-Path $ProjectPath)) {
    throw "Project folder not found: $ProjectPath"
}

Copy-Item `
    -Path (Join-Path $PSScriptRoot "*") `
    -Destination $ProjectPath `
    -Recurse `
    -Force

Set-Location $ProjectPath

Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v85_01_to_v85_08.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_dashboard_v2_v85_01_to_v85_08 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] STATE EXPORT"
python tools\export_dashboard_v2_state.py
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_dashboard_v2_v85_01_to_v85_08.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  dashboard_v2 `
  tools/export_dashboard_v2_state.py `
  tools/test_dashboard_v2_v85_01_to_v85_08.py `
  tools/install_check_v85_01_to_v85_08.py `
  tools/verify_dashboard_v2_v85_01_to_v85_08.py `
  RUN_V85_01_TO_V85_08_DASHBOARD_V2.ps1 `
  RUN_V85_01_TO_V85_08_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V85_01_TO_V85_08_ONE_CLICK.ps1 `
  release/v85_01_to_v85_08 `
  V85_01_TO_V85_08_MANIFEST.json `
  GIT_COMMIT_V85_01_TO_V85_08.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V85.01-V85.08 dashboard v2 integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V85.01-V85.08 changes to commit."
}

Write-Host "[6/6] GIT PUSH"
if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "PUSH FAILED" }
}
else {
    Write-Host "Push skipped."
}

git log -1 --oneline
Write-Host "V85.01-V85.08 ONE-CLICK COMPLETE"
Write-Host "START DASHBOARD:"
Write-Host "powershell -ExecutionPolicy Bypass -File .\RUN_V85_01_TO_V85_08_DASHBOARD_V2.ps1"
