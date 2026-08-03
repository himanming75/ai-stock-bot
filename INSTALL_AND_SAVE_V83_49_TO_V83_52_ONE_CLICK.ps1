param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$ZipPath = "$env:USERPROFILE\Downloads\V83_49_TO_V83_52_SUPERVISED_REENTRY_RUNNER_ONE_CLICK.zip",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$TempPath = "$env:USERPROFILE\Downloads\V83_49_TO_V83_52_SUPERVISED_REENTRY_RUNNER_TEMP"

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

python tools\install_check_v83_49_to_v83_52.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

python -m unittest `
  tools.test_supervised_reentry_runner_v83_49_to_v83_52 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_49_TO_V83_52_SUPERVISED_REENTRY_RUNNER.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

python tools\verify_supervised_reentry_runner_v83_49_to_v83_52.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

git add `
  paper_runtime/supervised_reentry_runner_v83_49_52.py `
  dashboard/supervised_reentry_runner_integration.py `
  tools/run_supervised_reentry_runner_v83_49_to_v83_52.py `
  tools/test_supervised_reentry_runner_v83_49_to_v83_52.py `
  tools/install_check_v83_49_to_v83_52.py `
  tools/verify_supervised_reentry_runner_v83_49_to_v83_52.py `
  RUN_V83_49_TO_V83_52_SUPERVISED_REENTRY_RUNNER.ps1 `
  RUN_V83_49_TO_V83_52_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_49_TO_V83_52_ONE_CLICK.ps1 `
  release/v83_49_to_v83_52 `
  V83_49_TO_V83_52_MANIFEST.json `
  GIT_COMMIT_V83_49_TO_V83_52.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.49-V83.52 supervised re-entry runner integrated"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}

if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "PUSH FAILED" }
}

git log -1 --oneline
Write-Host "V83.49-V83.52 ONE-CLICK COMPLETE"
