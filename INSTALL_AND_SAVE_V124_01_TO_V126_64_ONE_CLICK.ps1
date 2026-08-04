param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop"
$SourceRoot=$PSScriptRoot
if([string]::IsNullOrWhiteSpace($SourceRoot)){$SourceRoot=Split-Path -Parent $MyInvocation.MyCommand.Path}
if([string]::IsNullOrWhiteSpace($SourceRoot)){throw "SOURCE PATH ERROR"}
Write-Host "=== V124.01-V126.64 FAST TRACK F ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
 Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v124_01_to_v126_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v124_01_to_v126_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] OFFLINE RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V124_01_TO_V126_64.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v124_01_to_v126_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add continuous_paper_shadow tools/run_v124_01_to_v126_64.py `
 tools/test_v124_01_to_v126_64.py tools/install_check_v124_01_to_v126_64.py `
 tools/verify_v124_01_to_v126_64.py RUN_V124_01_TO_V126_64.ps1 `
 RUN_V124_TO_V126_REAL_SHADOW.ps1 RUN_V124_TO_V126_AUTOMATED_PAPER_CYCLE.ps1 `
 RUN_V124_01_TO_V126_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V124_01_TO_V126_64_ONE_CLICK.ps1 `
 release/v124_01_to_v126_64 V124_01_TO_V126_64_MANIFEST.json `
 GIT_COMMIT_V124_01_TO_V126_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V124.01-V126.64 continuous Alpaca Paper shadow qualification integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V124.01-V126.64 ONE-CLICK COMPLETE"
