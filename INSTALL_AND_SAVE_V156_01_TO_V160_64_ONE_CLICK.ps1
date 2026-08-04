param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V156.01-V160.64 SCHEDULER RECOVERY NOTIFICATIONS ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force}
Set-Location $ProjectPath
Write-Host "[1/5] INSTALL CHECK";python tools\install_check_v156_01_to_v160_64.py;if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/5] TEST";python -m unittest tools.test_v156_01_to_v160_64 -v;if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/5] VERIFY";python tools\verify_v156_01_to_v160_64.py;if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[4/5] GIT COMMIT"
git add operations_manager web_controller/operations_api.py web_controller/server.py web_controller/static `
 release/v156_01_to_v160_64 tools/run_v156_operations_job.py `
 tools/test_v156_01_to_v160_64.py tools/install_check_v156_01_to_v160_64.py `
 tools/verify_v156_01_to_v160_64.py RUN_V156_01_TO_V160_64_TEST_AND_VERIFY.ps1 `
 RUN_V156_PRE_MARKET_JOB.ps1 RUN_V156_INTRADAY_SHADOW_JOB.ps1 `
 RUN_V156_POST_MARKET_JOB.ps1 RUN_V156_HEALTH_CHECK.ps1 `
 RUN_V156_CREATE_RECOVERY_PLAN.ps1 INSTALL_AND_SAVE_V156_01_TO_V160_64_ONE_CLICK.ps1 `
 V156_01_TO_V160_64_MANIFEST.json GIT_COMMIT_V156_01_TO_V160_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V156.01-V160.64 scheduler recovery notifications integrated"}
Write-Host "[5/5] GIT PUSH";if(-not $SkipPush){git push origin main};git log -1 --oneline
Write-Host "V156.01-V160.64 ONE-CLICK COMPLETE"
Write-Host "Restart the web controller to load Scheduler & Recovery."
