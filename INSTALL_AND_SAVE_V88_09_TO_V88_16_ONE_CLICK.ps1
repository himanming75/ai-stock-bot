param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V88.09-V88.16 ONE-CLICK INSTALL ==="
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
python tools\install_check_v88_09_to_v88_16.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_paper_orchestrator_v88_09_to_v88_16 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V88_09_TO_V88_16_PAPER_ORCHESTRATOR.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_paper_orchestrator_v88_09_to_v88_16.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  paper_orchestrator `
  dashboard_v2/paper_orchestrator_integration.py `
  tools/run_paper_orchestrator_v88_09_to_v88_16.py `
  tools/test_paper_orchestrator_v88_09_to_v88_16.py `
  tools/install_check_v88_09_to_v88_16.py `
  tools/verify_paper_orchestrator_v88_09_to_v88_16.py `
  RUN_V88_09_TO_V88_16_PAPER_ORCHESTRATOR.ps1 `
  RUN_V88_09_TO_V88_16_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V88_09_TO_V88_16_ONE_CLICK.ps1 `
  release/v88_09_to_v88_16 `
  V88_09_TO_V88_16_MANIFEST.json `
  GIT_COMMIT_V88_09_TO_V88_16.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V88.09-V88.16 paper orchestrator compatibility fixed"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V88.09-V88.16 changes to commit."
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
Write-Host "V88.09-V88.16 ONE-CLICK COMPLETE"
