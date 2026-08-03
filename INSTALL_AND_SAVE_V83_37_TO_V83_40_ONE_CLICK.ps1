param(
    [string]$ProjectPath = "C:\stock-bot",
    [string]$ZipPath = "$env:USERPROFILE\Downloads\V83_37_TO_V83_40_TRIGGER_CHAIN_RETRY_POLICY_ONE_CLICK.zip",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
$TempPath = Join-Path $env:USERPROFILE `
    "Downloads\V83_37_TO_V83_40_TRIGGER_CHAIN_RETRY_POLICY_TEMP"

Write-Host "=== V83.37-V83.40 ONE-CLICK INSTALL AND SAVE ==="

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
Copy-Item (Join-Path $TempPath "*") $ProjectPath -Recurse -Force
Set-Location $ProjectPath

Write-Host "[1/7] Checking local base and pushing pending commit..."
$Head = (git rev-parse --short HEAD).Trim()
Write-Host "Current local HEAD: $Head"
if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) {
        throw "PREVIOUS COMMIT PUSH FAILED"
    }
}

Write-Host "[2/7] Install check..."
python tools\install_check_v83_37_to_v83_40.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL CHECK FAILED" }

Write-Host "[3/7] Unit tests..."
python -m unittest `
  tools.test_trigger_chain_retry_policy_v83_37_to_v83_40 `
  -v
if ($LASTEXITCODE -ne 0) { throw "UNIT TEST FAILED" }

Write-Host "[4/7] Base run..."
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_37_TO_V83_40_TRIGGER_CHAIN_RETRY_POLICY.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[5/7] Verify..."
python tools\verify_trigger_chain_retry_policy_v83_37_to_v83_40.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[6/7] Stage and commit only this stage..."
git add `
  paper_runtime/trigger_chain_retry_policy_v83_37_40.py `
  dashboard/trigger_chain_retry_policy_integration.py `
  tools/run_trigger_chain_retry_policy_v83_37_to_v83_40.py `
  tools/test_trigger_chain_retry_policy_v83_37_to_v83_40.py `
  tools/install_check_v83_37_to_v83_40.py `
  tools/verify_trigger_chain_retry_policy_v83_37_to_v83_40.py `
  RUN_V83_37_TO_V83_40_TRIGGER_CHAIN_RETRY_POLICY.ps1 `
  RUN_V83_37_TO_V83_40_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_37_TO_V83_40_ONE_CLICK.ps1 `
  release/v83_37_to_v83_40 `
  V83_37_TO_V83_40_MANIFEST.json `
  GIT_COMMIT_V83_37_TO_V83_40.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m `
      "V83.37-V83.40 trigger chain retry policy and budget implemented"
    if ($LASTEXITCODE -ne 0) { throw "GIT COMMIT FAILED" }
}
else {
    Write-Host "No new V83.37-V83.40 changes to commit."
}

Write-Host "[7/7] Push..."
if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "GIT PUSH FAILED" }
}
else {
    Write-Host "Push skipped."
}

Write-Host "=== V83.37-V83.40 COMPLETE ==="
git log -2 --oneline
Write-Host "Other existing modified/untracked files were not staged."
