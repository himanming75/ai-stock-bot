param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V256.01-V260.64 AUTONOMOUS PAPER TRADING ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v256_01_to_v260_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v256_01_to_v260_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] DRY RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V256_01_TO_V260_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v256_01_to_v260_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add autonomous_paper_trading web_controller/autonomous_paper_api.py `
 release/v256_01_to_v260_64 tools/run_v256_01_to_v260_64.py `
 tools/test_v256_01_to_v260_64.py tools/install_check_v256_01_to_v260_64.py `
 tools/verify_v256_01_to_v260_64.py RUN_V256_01_TO_V260_64_DRY_RUN.ps1 `
 RUN_V256_01_TO_V260_64_REAL_PAPER.ps1 ENABLE_V256_AUTONOMOUS_PAPER.ps1 `
 DISABLE_V256_AUTONOMOUS_PAPER.ps1 RUN_V256_01_TO_V260_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V256_01_TO_V260_64_ONE_CLICK.ps1 `
 V256_01_TO_V260_64_MANIFEST.json GIT_COMMIT_V256_01_TO_V260_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V256.01-V260.64 autonomous paper trading integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V256.01-V260.64 ONE-CLICK COMPLETE"
Write-Host "Default state is SAFE/BLOCKED."
Write-Host "Enable later with .\ENABLE_V256_AUTONOMOUS_PAPER.ps1"
