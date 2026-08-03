param([string]$ProjectPath="C:\stock-bot",[string]$ZipPath="$env:USERPROFILE\Downloads\V83_41_TO_V83_44_RETRY_APPROVAL_SUPERVISED_REENTRY_ONE_CLICK.zip",[switch]$SkipPush)
$ErrorActionPreference="Stop"
$TempPath="$env:USERPROFILE\Downloads\V83_41_TO_V83_44_RETRY_APPROVAL_SUPERVISED_REENTRY_TEMP"
if(Test-Path $TempPath){Remove-Item $TempPath-Recurse-Force}
Expand-Archive -Path $ZipPath -DestinationPath $TempPath -Force
Copy-Item "$TempPath\*" $ProjectPath -Recurse -Force
Set-Location $ProjectPath
python tools\install_check_v83_41_to_v83_44.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
python -m unittest tools.test_retry_approval_supervised_reentry_v83_41_to_v83_44 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
powershell -ExecutionPolicy Bypass -File .\RUN_V83_41_TO_V83_44_RETRY_APPROVAL_SUPERVISED_REENTRY.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
python tools\verify_retry_approval_supervised_reentry_v83_41_to_v83_44.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
git add paper_runtime/retry_approval_supervised_reentry_v83_41_44.py dashboard/retry_approval_supervised_reentry_integration.py tools/run_retry_approval_supervised_reentry_v83_41_to_v83_44.py tools/test_retry_approval_supervised_reentry_v83_41_to_v83_44.py tools/install_check_v83_41_to_v83_44.py tools/verify_retry_approval_supervised_reentry_v83_41_to_v83_44.py RUN_V83_41_TO_V83_44_RETRY_APPROVAL_SUPERVISED_REENTRY.ps1 RUN_V83_41_TO_V83_44_TEST_AND_VERIFY.ps1 INSTALL_AND_SAVE_V83_41_TO_V83_44_ONE_CLICK.ps1 release/v83_41_to_v83_44 V83_41_TO_V83_44_MANIFEST.json GIT_COMMIT_V83_41_TO_V83_44.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V83.41-V83.44 retry approval and supervised re-entry implemented"}
if(-not $SkipPush){git push origin main}
git log -1 --oneline
