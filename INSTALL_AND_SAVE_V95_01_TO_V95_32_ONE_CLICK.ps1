param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop"
Copy-Item -Path (Join-Path $PSScriptRoot "*") -Destination $ProjectPath -Recurse -Force
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK";python tools\install_check_v95_01_to_v95_32.py;if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] UNIT TEST";python -m unittest tools.test_v95_01_to_v95_32 -v;if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] BASE RUN";powershell -ExecutionPolicy Bypass -File .\RUN_V95_01_TO_V95_32.ps1;if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY";python tools\verify_v95_01_to_v95_32.py;if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add paper_execution_simulator tools/run_v95_01_to_v95_32.py tools/test_v95_01_to_v95_32.py tools/install_check_v95_01_to_v95_32.py tools/verify_v95_01_to_v95_32.py RUN_V95_01_TO_V95_32.ps1 RUN_V95_01_TO_V95_32_TEST_AND_VERIFY.ps1 INSTALL_AND_SAVE_V95_01_TO_V95_32_ONE_CLICK.ps1 release/v95_01_to_v95_32 V95_01_TO_V95_32_MANIFEST.json GIT_COMMIT_V95_01_TO_V95_32.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V95.01-V95.32 paper execution simulator integrated";if($LASTEXITCODE-ne 0){throw "COMMIT FAILED"}}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main;if($LASTEXITCODE-ne 0){throw "PUSH FAILED"}}
git log -1 --oneline
Write-Host "V95.01-V95.32 ONE-CLICK COMPLETE"
