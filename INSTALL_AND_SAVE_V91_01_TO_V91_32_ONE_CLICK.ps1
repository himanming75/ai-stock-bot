param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop"
Copy-Item -Path (Join-Path $PSScriptRoot "*") -Destination $ProjectPath -Recurse -Force
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK";python tools\install_check_v91_01_to_v91_32.py;if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] UNIT TEST";python -m unittest tools.test_v91_01_to_v91_32 -v;if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] BASE RUN";powershell -ExecutionPolicy Bypass -File .\RUN_V91_01_TO_V91_32.ps1;if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY";python tools\verify_v91_01_to_v91_32.py;if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add strategy_lab tools/run_v91_01_to_v91_32.py tools/test_v91_01_to_v91_32.py tools/install_check_v91_01_to_v91_32.py tools/verify_v91_01_to_v91_32.py RUN_V91_01_TO_V91_32.ps1 RUN_V91_01_TO_V91_32_TEST_AND_VERIFY.ps1 INSTALL_AND_SAVE_V91_01_TO_V91_32_ONE_CLICK.ps1 release/v91_01_to_v91_32 V91_01_TO_V91_32_MANIFEST.json GIT_COMMIT_V91_01_TO_V91_32.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V91.01-V91.32 ultimate strategy lab integrated";if($LASTEXITCODE-ne 0){throw "COMMIT FAILED"}}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main;if($LASTEXITCODE-ne 0){throw "PUSH FAILED"}}
git log -1 --oneline
Write-Host "V91.01-V91.32 ONE-CLICK COMPLETE"
