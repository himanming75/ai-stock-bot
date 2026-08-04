param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V196.01-V200.64 MULTI-BROKER MULTI-ACCOUNT PRODUCTION ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK";python tools\install_check_v196_01_to_v200_64.py;if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST";python -m unittest tools.test_v196_01_to_v200_64 -v;if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] RUN";powershell -ExecutionPolicy Bypass -File .\RUN_V196_01_TO_V200_64.ps1;if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY";python tools\verify_v196_01_to_v200_64.py;if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add multi_broker_production web_controller/multi_broker_api.py release/v196_01_to_v200_64 `
 tools/run_v196_01_to_v200_64.py tools/test_v196_01_to_v200_64.py `
 tools/install_check_v196_01_to_v200_64.py tools/verify_v196_01_to_v200_64.py `
 RUN_V196_01_TO_V200_64.ps1 RUN_V196_01_TO_V200_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V196_01_TO_V200_64_ONE_CLICK.ps1 `
 V196_01_TO_V200_64_MANIFEST.json GIT_COMMIT_V196_01_TO_V200_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V196.01-V200.64 multi-broker multi-account production integrated"}
Write-Host "[6/6] GIT PUSH";if(-not $SkipPush){git push origin main};git log -1 --oneline
Write-Host "V196.01-V200.64 ONE-CLICK COMPLETE"
