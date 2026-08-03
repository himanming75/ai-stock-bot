param(
    [string]$ProjectPath="C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference="Stop"

Copy-Item `
    -Path (Join-Path $PSScriptRoot "*") `
    -Destination $ProjectPath `
    -Recurse `
    -Force

Set-Location $ProjectPath

Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v97_33_to_v97_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}

Write-Host "[2/6] UNIT TEST"
python -m unittest tools.test_v97_33_to_v97_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
    -File .\RUN_V97_33_TO_V97_64.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}

Write-Host "[4/6] VERIFY"
python tools\verify_v97_33_to_v97_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}

Write-Host "[5/6] GIT COMMIT"
git add `
    paper_broker_read_model `
    tools/run_v97_33_to_v97_64.py `
    tools/test_v97_33_to_v97_64.py `
    tools/install_check_v97_33_to_v97_64.py `
    tools/verify_v97_33_to_v97_64.py `
    RUN_V97_33_TO_V97_64.ps1 `
    RUN_V97_33_TO_V97_64_TEST_AND_VERIFY.ps1 `
    INSTALL_AND_SAVE_V97_33_TO_V97_64_ONE_CLICK.ps1 `
    release/v97_33_to_v97_64 `
    V97_33_TO_V97_64_MANIFEST.json `
    GIT_COMMIT_V97_33_TO_V97_64.txt `
    GIT_COMMIT_V97_33_TO_V97_64_FIXED.txt

$staged=git diff --cached --name-only
if($staged){
    git commit -m "V97.33-V97.64 fix internal market value reconciliation"
    if($LASTEXITCODE-ne 0){throw "COMMIT FAILED"}
}

Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){
    git push origin main
    if($LASTEXITCODE-ne 0){throw "PUSH FAILED"}
}

git log -1 --oneline
Write-Host "V97.33-V97.64 FIXED ONE-CLICK COMPLETE"
