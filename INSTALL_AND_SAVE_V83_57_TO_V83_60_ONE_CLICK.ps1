param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$ZipPath = "$env:USERPROFILE\Downloads\V83_57_TO_V83_60_FULL_SCHEDULE_COMPLETION_ORCHESTRATOR_ONE_CLICK.zip",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$TempPath = "$env:USERPROFILE\Downloads\V83_57_TO_V83_60_FULL_SCHEDULE_COMPLETION_ORCHESTRATOR_TEMP"

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

python tools\install_check_v83_57_to_v83_60.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

python -m unittest `
  tools.test_full_schedule_completion_orchestrator_v83_57_to_v83_60 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_57_TO_V83_60_FULL_SCHEDULE_COMPLETION_ORCHESTRATOR.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

python tools\verify_full_schedule_completion_orchestrator_v83_57_to_v83_60.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

git add `
  paper_runtime/full_schedule_completion_orchestrator_v83_57_60.py `
  dashboard/full_schedule_completion_orchestrator_integration.py `
  tools/run_full_schedule_completion_orchestrator_v83_57_to_v83_60.py `
  tools/test_full_schedule_completion_orchestrator_v83_57_to_v83_60.py `
  tools/install_check_v83_57_to_v83_60.py `
  tools/verify_full_schedule_completion_orchestrator_v83_57_to_v83_60.py `
  RUN_V83_57_TO_V83_60_FULL_SCHEDULE_COMPLETION_ORCHESTRATOR.ps1 `
  RUN_V83_57_TO_V83_60_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_57_TO_V83_60_ONE_CLICK.ps1 `
  release/v83_57_to_v83_60 `
  V83_57_TO_V83_60_MANIFEST.json `
  GIT_COMMIT_V83_57_TO_V83_60.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.57-V83.60 full schedule completion orchestrator implemented"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}

if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "PUSH FAILED" }
}

git log -1 --oneline
Write-Host "V83.57-V83.60 ONE-CLICK COMPLETE"
