param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop"
Copy-Item -Path (Join-Path $PSScriptRoot "*") -Destination $ProjectPath -Recurse -Force
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v89_33_to_v89_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] UNIT TEST"
python -m unittest tools.test_v89_33_to_v89_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V89_33_TO_V89_64.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v89_33_to_v89_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add v89_portfolio tools/run_v89_33_to_v89_64.py tools/test_v89_33_to_v89_64.py tools/install_check_v89_33_to_v89_64.py tools/verify_v89_33_to_v89_64.py RUN_V89_33_TO_V89_64.ps1 RUN_V89_33_TO_V89_64_TEST_AND_VERIFY.ps1 INSTALL_AND_SAVE_V89_33_TO_V89_64_ONE_CLICK.ps1 release/v89_33_to_v89_64 V89_33_TO_V89_64_MANIFEST.json GIT_COMMIT_V89_33_TO_V89_64.txt
$staged=git diff --cached --name-only
if($staged){
 git commit -m "V89.33-V89.64 source recovery and verification fixed"
 if($LASTEXITCODE-ne 0){throw "COMMIT FAILED"}
}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){
 git push origin main
 if($LASTEXITCODE-ne 0){throw "PUSH FAILED"}
}
git log -1 --oneline
Write-Host "V89.33-V89.64 ONE-CLICK COMPLETE"
