param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V306.01-V310.64 REAL PAPER MICRO ORDER VALIDATION ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v306_01_to_v310_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v306_01_to_v310_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] DRY RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V306_01_TO_V310_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v306_01_to_v310_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add real_paper_micro_order release/v306_01_to_v310_64 `
 tools/run_v306_01_to_v310_64.py tools/test_v306_01_to_v310_64.py `
 tools/install_check_v306_01_to_v310_64.py tools/verify_v306_01_to_v310_64.py `
 RUN_V306_01_TO_V310_64_DRY_RUN.ps1 RUN_V306_01_TO_V310_64_PAPER_PREFLIGHT.ps1 `
 ENABLE_V306_ONE_MICRO_PAPER_ORDER.ps1 SUBMIT_V306_ONE_MICRO_PAPER_ORDER.ps1 `
 DISABLE_V306_MICRO_PAPER_ORDER.ps1 RUN_V306_01_TO_V310_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V306_01_TO_V310_64_ONE_CLICK.ps1 `
 V306_01_TO_V310_64_MANIFEST.json GIT_COMMIT_V306_01_TO_V310_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V306.01-V310.64 real paper micro order validation integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V306.01-V310.64 ONE-CLICK COMPLETE"
Write-Host "Installation submitted ZERO Paper orders."
