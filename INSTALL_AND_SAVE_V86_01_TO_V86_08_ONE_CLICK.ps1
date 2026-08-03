param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V86.01-V86.08 ONE-CLICK INSTALL ==="
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
python tools\install_check_v86_01_to_v86_08.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_strategy_engine_v2_v86_01_to_v86_08 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_01_TO_V86_08_STRATEGY_ENGINE_V2.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_strategy_engine_v2_v86_01_to_v86_08.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  strategy_engine_v2 `
  dashboard_v2/strategy_integration.py `
  tools/run_strategy_engine_v2_v86_01_to_v86_08.py `
  tools/test_strategy_engine_v2_v86_01_to_v86_08.py `
  tools/install_check_v86_01_to_v86_08.py `
  tools/verify_strategy_engine_v2_v86_01_to_v86_08.py `
  RUN_V86_01_TO_V86_08_STRATEGY_ENGINE_V2.ps1 `
  RUN_V86_01_TO_V86_08_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V86_01_TO_V86_08_ONE_CLICK.ps1 `
  release/v86_01_to_v86_08 `
  V86_01_TO_V86_08_MANIFEST.json `
  GIT_COMMIT_V86_01_TO_V86_08.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V86.01-V86.08 AI strategy engine v2 integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V86.01-V86.08 changes to commit."
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
Write-Host "V86.01-V86.08 ONE-CLICK COMPLETE"
