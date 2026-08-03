param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V83.69-V83.72 ONE-CLICK INSTALL ==="
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
python tools\install_check_v83_69_to_v83_72.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_operator_control_center_v83_69_to_v83_72 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_69_TO_V83_72_OPERATOR_CONTROL_CENTER.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_operator_control_center_v83_69_to_v83_72.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  paper_runtime/operator_control_center_v83_69_72.py `
  dashboard/operator_control_center_integration.py `
  tools/run_operator_control_center_v83_69_to_v83_72.py `
  tools/test_operator_control_center_v83_69_to_v83_72.py `
  tools/install_check_v83_69_to_v83_72.py `
  tools/verify_operator_control_center_v83_69_to_v83_72.py `
  RUN_V83_69_TO_V83_72_OPERATOR_CONTROL_CENTER.ps1 `
  RUN_V83_69_TO_V83_72_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_69_TO_V83_72_ONE_CLICK.ps1 `
  release/v83_69_to_v83_72 `
  V83_69_TO_V83_72_MANIFEST.json `
  GIT_COMMIT_V83_69_TO_V83_72.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.69-V83.72 operator control center and unified dashboard implemented"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V83.69-V83.72 changes to commit."
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
Write-Host "V83.69-V83.72 ONE-CLICK COMPLETE"
