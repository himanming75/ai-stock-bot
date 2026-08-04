param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop"
$SourceRoot=$PSScriptRoot
Write-Host "=== V146.01-V150.64 STRATEGY MANAGER FIXED V2 ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force}
Set-Location $ProjectPath
Write-Host "[1/5] INSTALL CHECK"
python tools\install_check_v146_01_to_v150_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/5] TEST"
python -m unittest tools.test_v146_01_to_v150_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/5] VERIFY"
python tools\verify_v146_01_to_v150_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[4/5] GIT COMMIT"
git add strategy_manager web_controller/server.py web_controller/strategy_api.py web_controller/static `
 release/v146_01_to_v150_64 tools/test_v146_01_to_v150_64.py `
 tools/install_check_v146_01_to_v150_64.py tools/verify_v146_01_to_v150_64.py `
 RUN_V146_01_TO_V150_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V146_01_TO_V150_64_ONE_CLICK.ps1 `
 V146_01_TO_V150_64_MANIFEST.json GIT_COMMIT_V146_01_TO_V150_64.txt `
 GIT_COMMIT_V146_01_TO_V150_64_FIXED_V2.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V146.01-V150.64 fix strategy default configuration isolation"}
Write-Host "[5/5] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V146.01-V150.64 FIXED V2 ONE-CLICK COMPLETE"
Write-Host "Restart the web controller to load the new Strategy tab."
