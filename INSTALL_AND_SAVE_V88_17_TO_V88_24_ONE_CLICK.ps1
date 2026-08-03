param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$BackupRoot = "C:\stock-bot-backups",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V88.17-V88.24 ONE-CLICK INSTALL ==="
Write-Host "Source:  $PSScriptRoot"
Write-Host "Project: $ProjectPath"

if (-not (Test-Path $ProjectPath)) {
    throw "Project folder not found: $ProjectPath"
}

Write-Host "[0/7] PRE-INSTALL STRUCTURE CHECK"
$IndicatorLayout = ""
if (Test-Path (Join-Path $ProjectPath "indicator_engine")) {
    $IndicatorLayout = "indicator_engine"
}
elseif (Test-Path (Join-Path $ProjectPath "indicator_engine_v2")) {
    $IndicatorLayout = "indicator_engine_v2"
}
else {
    throw "Neither indicator_engine nor indicator_engine_v2 exists."
}
Write-Host "Detected indicator layout: $IndicatorLayout"

Write-Host "[1/7] BACKUP"
powershell -ExecutionPolicy Bypass `
  -File "$PSScriptRoot\BACKUP_V88_17_TO_V88_24.ps1" `
  -ProjectPath $ProjectPath `
  -BackupRoot $BackupRoot
if ($LASTEXITCODE -ne 0) { throw "BACKUP FAILED" }

Write-Host "[2/7] INSTALL"
Copy-Item `
    -Path (Join-Path $PSScriptRoot "*") `
    -Destination $ProjectPath `
    -Recurse `
    -Force
Set-Location $ProjectPath

Write-Host "[3/7] INSTALL CHECK"
python tools\install_check_v88_17_to_v88_24.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL CHECK FAILED" }

Write-Host "[4/7] UNIT TEST"
python -m unittest `
  tools.test_paper_production_release_v88_17_to_v88_24 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[5/7] BASE RUN AND VERIFY"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V88_17_TO_V88_24_PAPER_PRODUCTION_RELEASE.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

python tools\verify_paper_production_release_v88_17_to_v88_24.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[6/7] GIT COMMIT"
git add `
  paper_production_release `
  dashboard_v2/paper_production_release_integration.py `
  tools/run_paper_production_release_v88_17_to_v88_24.py `
  tools/test_paper_production_release_v88_17_to_v88_24.py `
  tools/install_check_v88_17_to_v88_24.py `
  tools/verify_paper_production_release_v88_17_to_v88_24.py `
  BACKUP_V88_17_TO_V88_24.ps1 `
  ROLLBACK_V88_17_TO_V88_24.ps1 `
  RUN_V88_17_TO_V88_24_PAPER_PRODUCTION_RELEASE.ps1 `
  RUN_V88_17_TO_V88_24_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V88_17_TO_V88_24_ONE_CLICK.ps1 `
  release/v88_17_to_v88_24 `
  V88_17_TO_V88_24_MANIFEST.json `
  GIT_COMMIT_V88_17_TO_V88_24.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V88.17-V88.24 production release import path fixed"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V88.17-V88.24 changes to commit."
}

Write-Host "[7/7] GIT PUSH"
if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "PUSH FAILED" }
}
else {
    Write-Host "Push skipped."
}

git log -1 --oneline
Write-Host "V88.17-V88.24 ONE-CLICK COMPLETE"
