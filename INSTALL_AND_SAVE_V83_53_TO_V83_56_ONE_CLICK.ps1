param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$ZipPath = "$env:USERPROFILE\Downloads\V83_53_TO_V83_56_RETRY_CYCLE_COMPLETION_ONE_CLICK.zip",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$TempPath = "$env:USERPROFILE\Downloads\V83_53_TO_V83_56_RETRY_CYCLE_COMPLETION_TEMP"

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

python tools\install_check_v83_53_to_v83_56.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

python -m unittest `
  tools.test_retry_cycle_completion_v83_53_to_v83_56 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_53_TO_V83_56_RETRY_CYCLE_COMPLETION.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

python tools\verify_retry_cycle_completion_v83_53_to_v83_56.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

git add `
  paper_runtime/retry_cycle_completion_v83_53_56.py `
  dashboard/retry_cycle_completion_integration.py `
  tools/run_retry_cycle_completion_v83_53_to_v83_56.py `
  tools/test_retry_cycle_completion_v83_53_to_v83_56.py `
  tools/install_check_v83_53_to_v83_56.py `
  tools/verify_retry_cycle_completion_v83_53_to_v83_56.py `
  RUN_V83_53_TO_V83_56_RETRY_CYCLE_COMPLETION.ps1 `
  RUN_V83_53_TO_V83_56_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_53_TO_V83_56_ONE_CLICK.ps1 `
  release/v83_53_to_v83_56 `
  V83_53_TO_V83_56_MANIFEST.json `
  GIT_COMMIT_V83_53_TO_V83_56.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.53-V83.56 retry cycle completion and certificate implemented"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}

if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "PUSH FAILED" }
}

git log -1 --oneline
Write-Host "V83.53-V83.56 ONE-CLICK COMPLETE"
