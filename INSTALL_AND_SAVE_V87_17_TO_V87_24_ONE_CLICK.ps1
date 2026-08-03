param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V87.17-V87.24 ONE-CLICK INSTALL ==="
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
python tools\install_check_v87_17_to_v87_24.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_multi_asset_backtest_v87_17_to_v87_24 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V87_17_TO_V87_24_MULTI_ASSET_BACKTEST.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_multi_asset_backtest_v87_17_to_v87_24.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  multi_asset_backtest `
  dashboard_v2/multi_asset_backtest_integration.py `
  tools/run_multi_asset_backtest_v87_17_to_v87_24.py `
  tools/test_multi_asset_backtest_v87_17_to_v87_24.py `
  tools/install_check_v87_17_to_v87_24.py `
  tools/verify_multi_asset_backtest_v87_17_to_v87_24.py `
  RUN_V87_17_TO_V87_24_MULTI_ASSET_BACKTEST.ps1 `
  RUN_V87_17_TO_V87_24_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V87_17_TO_V87_24_ONE_CLICK.ps1 `
  release/v87_17_to_v87_24 `
  V87_17_TO_V87_24_MANIFEST.json `
  GIT_COMMIT_V87_17_TO_V87_24.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V87.17-V87.24 multi-asset backtest and benchmark integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V87.17-V87.24 changes to commit."
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
Write-Host "V87.17-V87.24 ONE-CLICK COMPLETE"
