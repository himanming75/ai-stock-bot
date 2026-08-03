param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V83.81-V83.88 ONE-CLICK INSTALL ==="
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
python tools\install_check_v83_81_to_v83_88.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_paper_stability_runtime_v83_81_to_v83_88 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_81_TO_V83_88_PAPER_STABILITY_RUNTIME.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_paper_stability_runtime_v83_81_to_v83_88.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  paper_runtime/paper_stability_runtime_v83_81_88.py `
  dashboard/paper_stability_runtime_integration.py `
  tools/run_paper_stability_runtime_v83_81_to_v83_88.py `
  tools/test_paper_stability_runtime_v83_81_to_v83_88.py `
  tools/install_check_v83_81_to_v83_88.py `
  tools/verify_paper_stability_runtime_v83_81_to_v83_88.py `
  RUN_V83_81_TO_V83_88_PAPER_STABILITY_RUNTIME.ps1 `
  RUN_V83_81_TO_V83_88_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_81_TO_V83_88_ONE_CLICK.ps1 `
  release/v83_81_to_v83_88 `
  V83_81_TO_V83_88_MANIFEST.json `
  GIT_COMMIT_V83_81_TO_V83_88.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.81-V83.88 paper stability and runtime readiness integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V83.81-V83.88 changes to commit."
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
Write-Host "V83.81-V83.88 ONE-CLICK COMPLETE"
