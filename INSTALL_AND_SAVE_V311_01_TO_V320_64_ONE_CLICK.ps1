param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V311.01-V320.64 REAL PAPER AUTONOMOUS DATA COLLECTION ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v311_01_to_v320_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v311_01_to_v320_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] DRY RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V311_01_TO_V320_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v311_01_to_v320_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add real_paper_data_collection web_controller/real_paper_data_collection_api.py `
 release/v311_01_to_v320_64 tools/run_v311_01_to_v320_64.py `
 tools/test_v311_01_to_v320_64.py tools/install_check_v311_01_to_v320_64.py `
 tools/verify_v311_01_to_v320_64.py RUN_V311_01_TO_V320_64_DRY_RUN.ps1 `
 RUN_V311_01_TO_V320_64_REAL_PAPER_SNAPSHOT.ps1 `
 RUN_V311_01_TO_V320_64_REAL_PAPER_SESSION.ps1 `
 ENABLE_V311_REAL_PAPER_DATA_COLLECTION.ps1 `
 DISABLE_V311_REAL_PAPER_DATA_COLLECTION.ps1 `
 RUN_V311_01_TO_V320_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V311_01_TO_V320_64_ONE_CLICK.ps1 `
 V311_01_TO_V320_64_MANIFEST.json GIT_COMMIT_V311_01_TO_V320_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V311.01-V320.64 real paper autonomous data collection integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V311.01-V320.64 ONE-CLICK COMPLETE"
Write-Host "Installation submitted ZERO new Paper orders."
