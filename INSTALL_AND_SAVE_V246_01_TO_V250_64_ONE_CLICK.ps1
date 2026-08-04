param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V246.01-V250.64 AI STRATEGY ENSEMBLE V3 ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v246_01_to_v250_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v246_01_to_v250_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V246_01_TO_V250_64.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v246_01_to_v250_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add ai_strategy_ensemble_v3 web_controller/strategy_ensemble_v3_api.py `
 release/v246_01_to_v250_64 tools/run_v246_01_to_v250_64.py `
 tools/test_v246_01_to_v250_64.py tools/install_check_v246_01_to_v250_64.py `
 tools/verify_v246_01_to_v250_64.py RUN_V246_01_TO_V250_64.ps1 `
 RUN_V246_01_TO_V250_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V246_01_TO_V250_64_ONE_CLICK.ps1 `
 V246_01_TO_V250_64_MANIFEST.json GIT_COMMIT_V246_01_TO_V250_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V246.01-V250.64 AI strategy ensemble v3 integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V246.01-V250.64 ONE-CLICK COMPLETE"
