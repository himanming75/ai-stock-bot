param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V83.89-V83.96 ONE-CLICK INSTALL ==="
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
python tools\install_check_v83_89_to_v83_96.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_performance_production_readiness_v83_89_to_v83_96 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_89_TO_V83_96_PERFORMANCE_READINESS.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_performance_production_readiness_v83_89_to_v83_96.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  paper_runtime/performance_production_readiness_v83_89_96.py `
  dashboard/performance_production_readiness_integration.py `
  tools/run_performance_production_readiness_v83_89_to_v83_96.py `
  tools/test_performance_production_readiness_v83_89_to_v83_96.py `
  tools/install_check_v83_89_to_v83_96.py `
  tools/verify_performance_production_readiness_v83_89_to_v83_96.py `
  RUN_V83_89_TO_V83_96_PERFORMANCE_READINESS.ps1 `
  RUN_V83_89_TO_V83_96_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_89_TO_V83_96_ONE_CLICK.ps1 `
  release/v83_89_to_v83_96 `
  V83_89_TO_V83_96_MANIFEST.json `
  GIT_COMMIT_V83_89_TO_V83_96.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.89-V83.96 performance and production readiness integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V83.89-V83.96 changes to commit."
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
Write-Host "V83.89-V83.96 ONE-CLICK COMPLETE"
