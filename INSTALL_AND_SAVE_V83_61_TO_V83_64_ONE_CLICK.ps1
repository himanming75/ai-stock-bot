param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$ZipPath = "$env:USERPROFILE\Downloads\V83_61_TO_V83_64_CRASH_RECOVERY_RESTART_CONTINUATION_ONE_CLICK.zip",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$TempPath = "$env:USERPROFILE\Downloads\V83_61_TO_V83_64_CRASH_RECOVERY_RESTART_CONTINUATION_TEMP"

if (-not (Test-Path $ZipPath)) {
    throw "ZIP file not found: $ZipPath"
}
if (-not (Test-Path $ProjectPath)) {
    throw "Project folder not found: $ProjectPath"
}
if (Test-Path $TempPath) {
    Remove-Item $TempPath -Recurse -Force
}

Expand-Archive -Path $ZipPath -DestinationPath $TempPath -Force
Copy-Item "$TempPath\*" $ProjectPath -Recurse -Force
Set-Location $ProjectPath

python tools\install_check_v83_61_to_v83_64.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

python -m unittest `
  tools.test_crash_recovery_restart_continuation_v83_61_to_v83_64 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_61_TO_V83_64_CRASH_RECOVERY_RESTART_CONTINUATION.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

python tools\verify_crash_recovery_restart_continuation_v83_61_to_v83_64.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

git add `
  paper_runtime/crash_recovery_restart_continuation_v83_61_64.py `
  dashboard/crash_recovery_restart_continuation_integration.py `
  tools/run_crash_recovery_restart_continuation_v83_61_to_v83_64.py `
  tools/test_crash_recovery_restart_continuation_v83_61_to_v83_64.py `
  tools/install_check_v83_61_to_v83_64.py `
  tools/verify_crash_recovery_restart_continuation_v83_61_to_v83_64.py `
  RUN_V83_61_TO_V83_64_CRASH_RECOVERY_RESTART_CONTINUATION.ps1 `
  RUN_V83_61_TO_V83_64_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_61_TO_V83_64_ONE_CLICK.ps1 `
  release/v83_61_to_v83_64 `
  V83_61_TO_V83_64_MANIFEST.json `
  GIT_COMMIT_V83_61_TO_V83_64.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.61-V83.64 crash recovery and restart continuation implemented"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}

if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "PUSH FAILED" }
}

git log -1 --oneline
Write-Host "V83.61-V83.64 ONE-CLICK COMPLETE"
