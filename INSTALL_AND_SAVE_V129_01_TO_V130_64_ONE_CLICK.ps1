param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop"
$SourceRoot=$PSScriptRoot
if([string]::IsNullOrWhiteSpace($SourceRoot)){$SourceRoot=Split-Path -Parent $MyInvocation.MyCommand.Path}
if([string]::IsNullOrWhiteSpace($SourceRoot)){throw "SOURCE PATH ERROR"}
Write-Host "=== V129.01-V130.64 RESTRICTED LIVE CANDIDATE ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
 Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v129_01_to_v130_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v129_01_to_v130_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V129_01_TO_V130_64.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v129_01_to_v130_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add restricted_live_candidate tools/run_v129_01_to_v130_64.py `
 tools/test_v129_01_to_v130_64.py tools/install_check_v129_01_to_v130_64.py `
 tools/verify_v129_01_to_v130_64.py RUN_V129_01_TO_V130_64.ps1 `
 RUN_V129_01_TO_V130_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V129_01_TO_V130_64_ONE_CLICK.ps1 `
 release/v129_01_to_v130_64 V129_01_TO_V130_64_MANIFEST.json `
 GIT_COMMIT_V129_01_TO_V130_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V129.01-V130.64 restricted automatic live candidate read-only gate integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V129.01-V130.64 ONE-CLICK COMPLETE"
