param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V88.01-V88.08 ONE-CLICK INSTALL ==="
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
python tools\install_check_v88_01_to_v88_08.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_web_ui_v2_v88_01_to_v88_08 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] STATE EXPORT"
python tools\export_web_ui_v2_state.py
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_web_ui_v2_v88_01_to_v88_08.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  web_ui_v2 `
  tools/test_web_ui_v2_v88_01_to_v88_08.py `
  tools/install_check_v88_01_to_v88_08.py `
  tools/export_web_ui_v2_state.py `
  tools/verify_web_ui_v2_v88_01_to_v88_08.py `
  RUN_V88_01_TO_V88_08_WEB_UI_V2.ps1 `
  RUN_V88_01_TO_V88_08_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V88_01_TO_V88_08_ONE_CLICK.ps1 `
  release/v88_01_to_v88_08 `
  V88_01_TO_V88_08_MANIFEST.json `
  GIT_COMMIT_V88_01_TO_V88_08.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V88.01-V88.08 web UI v2 integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V88.01-V88.08 changes to commit."
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
Write-Host "V88.01-V88.08 ONE-CLICK COMPLETE"
Write-Host "START WEB UI:"
Write-Host "powershell -ExecutionPolicy Bypass -File .\RUN_V88_01_TO_V88_08_WEB_UI_V2.ps1"
