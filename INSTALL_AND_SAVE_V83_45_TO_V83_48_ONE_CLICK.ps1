param([string]$ProjectPath="C:\stock-bot",[string]$ZipPath="$env:USERPROFILE\Downloads\V83_45_TO_V83_48_REENTRY_EXECUTION_GUARD_AUDIT_ONE_CLICK.zip",[switch]$SkipPush)
$ErrorActionPreference="Stop"
$TempPath="$env:USERPROFILE\Downloads\V83_45_TO_V83_48_REENTRY_EXECUTION_GUARD_AUDIT_TEMP"
if(-not(Test-Path $ZipPath)){throw "ZIP file not found: $ZipPath"}
if(-not(Test-Path $ProjectPath)){throw "Project folder not found: $ProjectPath"}
if(Test-Path $TempPath){Remove-Item $TempPath -Recurse -Force}
Expand-Archive -Path $ZipPath -DestinationPath $TempPath -Force
Copy-Item "$TempPath\*" $ProjectPath -Recurse -Force
Set-Location $ProjectPath
python tools\install_check_v83_45_to_v83_48.py
if($LASTEXITCODE -ne 0){throw "INSTALL FAILED"}
python -m unittest tools.test_reentry_execution_guard_audit_v83_45_to_v83_48 -v
if($LASTEXITCODE -ne 0){throw "TEST FAILED"}
powershell -ExecutionPolicy Bypass -File .\RUN_V83_45_TO_V83_48_REENTRY_EXECUTION_GUARD_AUDIT.ps1
if($LASTEXITCODE -ne 0){throw "RUN FAILED"}
python tools\verify_reentry_execution_guard_audit_v83_45_to_v83_48.py
if($LASTEXITCODE -ne 0){throw "VERIFY FAILED"}
git add paper_runtime/reentry_execution_guard_audit_v83_45_48.py dashboard/reentry_execution_guard_audit_integration.py tools/run_reentry_execution_guard_audit_v83_45_to_v83_48.py tools/test_reentry_execution_guard_audit_v83_45_to_v83_48.py tools/install_check_v83_45_to_v83_48.py tools/verify_reentry_execution_guard_audit_v83_45_to_v83_48.py RUN_V83_45_TO_V83_48_REENTRY_EXECUTION_GUARD_AUDIT.ps1 RUN_V83_45_TO_V83_48_TEST_AND_VERIFY.ps1 INSTALL_AND_SAVE_V83_45_TO_V83_48_ONE_CLICK.ps1 release/v83_45_to_v83_48 V83_45_TO_V83_48_MANIFEST.json GIT_COMMIT_V83_45_TO_V83_48.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V83.45-V83.48 re-entry execution guard and audit implemented"}
if(-not $SkipPush){git push origin main}
git log -1 --oneline
