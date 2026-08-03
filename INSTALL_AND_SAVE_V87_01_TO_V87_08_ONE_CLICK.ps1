param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V87.01-V87.08 ONE-CLICK INSTALL ==="
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
python tools\install_check_v87_01_to_v87_08.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_backtest_v2_v87_01_to_v87_08 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V87_01_TO_V87_08_BACKTEST_V2.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_backtest_v2_v87_01_to_v87_08.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  backtest_v2 `
  dashboard_v2/backtest_v2_integration.py `
  tools/run_backtest_v2_v87_01_to_v87_08.py `
  tools/test_backtest_v2_v87_01_to_v87_08.py `
  tools/install_check_v87_01_to_v87_08.py `
  tools/verify_backtest_v2_v87_01_to_v87_08.py `
  RUN_V87_01_TO_V87_08_BACKTEST_V2.ps1 `
  RUN_V87_01_TO_V87_08_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V87_01_TO_V87_08_ONE_CLICK.ps1 `
  release/v87_01_to_v87_08 `
  V87_01_TO_V87_08_MANIFEST.json `
  GIT_COMMIT_V87_01_TO_V87_08.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V87.01-V87.08 backtest engine v2 integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V87.01-V87.08 changes to commit."
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
Write-Host "V87.01-V87.08 ONE-CLICK COMPLETE"
