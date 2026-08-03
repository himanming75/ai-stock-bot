param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

Write-Host "=== V83.65-V83.68 FIXED2 ONE-CLICK INSTALL ==="
Write-Host "Source:  $PSScriptRoot"
Write-Host "Project: $ProjectPath"

if (-not (Test-Path $ProjectPath)) {
    throw "Project folder not found: $ProjectPath"
}

# Copy directly from the already extracted FIXED2 package.
# Do not reopen an older ZIP from Downloads.
Copy-Item `
    -Path (Join-Path $PSScriptRoot "*") `
    -Destination $ProjectPath `
    -Recurse `
    -Force

Set-Location $ProjectPath

Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v83_65_to_v83_68.py
if ($LASTEXITCODE -ne 0) { throw "INSTALL FAILED" }

Write-Host "[2/6] UNIT TEST"
python -m unittest `
  tools.test_end_to_end_paper_cycle_certification_v83_65_to_v83_68 `
  -v
if ($LASTEXITCODE -ne 0) { throw "TEST FAILED" }

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
  -File .\RUN_V83_65_TO_V83_68_END_TO_END_PAPER_CYCLE_CERTIFICATION.ps1
if ($LASTEXITCODE -ne 0) { throw "RUN FAILED" }

Write-Host "[4/6] VERIFY"
python tools\verify_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py
if ($LASTEXITCODE -ne 0) { throw "VERIFY FAILED" }

Write-Host "[5/6] GIT COMMIT"
git add `
  paper_runtime/end_to_end_paper_cycle_certification_v83_65_68.py `
  dashboard/end_to_end_paper_cycle_certification_integration.py `
  tools/run_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py `
  tools/test_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py `
  tools/install_check_v83_65_to_v83_68.py `
  tools/verify_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py `
  RUN_V83_65_TO_V83_68_END_TO_END_PAPER_CYCLE_CERTIFICATION.ps1 `
  RUN_V83_65_TO_V83_68_TEST_AND_VERIFY.ps1 `
  INSTALL_AND_SAVE_V83_65_TO_V83_68_ONE_CLICK.ps1 `
  release/v83_65_to_v83_68 `
  V83_65_TO_V83_68_MANIFEST.json `
  GIT_COMMIT_V83_65_TO_V83_68.txt

$Staged = git diff --cached --name-only
if ($Staged) {
    git commit -m "V83.65-V83.68 end-to-end paper cycle certification implemented"
    if ($LASTEXITCODE -ne 0) { throw "COMMIT FAILED" }
}
else {
    Write-Host "No new V83.65-V83.68 changes to commit."
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
Write-Host "V83.65-V83.68 FIXED2 ONE-CLICK COMPLETE"
