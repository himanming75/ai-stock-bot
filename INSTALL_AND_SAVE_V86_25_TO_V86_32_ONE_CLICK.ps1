param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V86.25-V86.32 ONE-CLICK INSTALL ==="
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
python tools\install_check_v86_25_to_v86_32.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_ai_explainability_v86_25_to_v86_32 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V86_25_TO_V86_32_AI_EXPLAINABILITY.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_ai_explainability_v86_25_to_v86_32.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  explainability_engine `
  dashboard_v2/explainability_integration.py `
  tools/run_ai_explainability_v86_25_to_v86_32.py `
  tools/test_ai_explainability_v86_25_to_v86_32.py `
  tools/install_check_v86_25_to_v86_32.py `
  tools/verify_ai_explainability_v86_25_to_v86_32.py `
  RUN_V86_25_TO_V86_32_AI_EXPLAINABILITY.ps1 `
  RUN_V86_25_TO_V86_32_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V86_25_TO_V86_32_ONE_CLICK.ps1 `
  release/v86_25_to_v86_32 `
  V86_25_TO_V86_32_MANIFEST.json `
  GIT_COMMIT_V86_25_TO_V86_32.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V86.25-V86.32 AI explainability engine integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V86.25-V86.32 changes to commit."
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
Write-Host "V86.25-V86.32 ONE-CLICK COMPLETE"
