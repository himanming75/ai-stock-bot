param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V171.01-V175.64 CONTROLLED MICRO-LIVE SAFETY REVIEW ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK";python tools\install_check_v171_01_to_v175_64.py;if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST";python -m unittest tools.test_v171_01_to_v175_64 -v;if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] RUN";powershell -ExecutionPolicy Bypass -File .\RUN_V171_01_TO_V175_64.ps1;if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY";python tools\verify_v171_01_to_v175_64.py;if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add controlled_micro_live web_controller/micro_live_api.py release/v171_01_to_v175_64 `
 tools/run_v171_01_to_v175_64.py tools/test_v171_01_to_v175_64.py `
 tools/install_check_v171_01_to_v175_64.py tools/verify_v171_01_to_v175_64.py `
 RUN_V171_01_TO_V175_64.ps1 RUN_V171_01_TO_V175_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V171_01_TO_V175_64_ONE_CLICK.ps1 `
 V171_01_TO_V175_64_MANIFEST.json GIT_COMMIT_V171_01_TO_V175_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V171.01-V175.64 controlled micro-live safety review integrated"}
Write-Host "[6/6] GIT PUSH";if(-not $SkipPush){git push origin main};git log -1 --oneline
Write-Host "V171.01-V175.64 ONE-CLICK COMPLETE"
