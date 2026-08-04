param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop"
$SourceRoot=$PSScriptRoot
if([string]::IsNullOrWhiteSpace($SourceRoot)){$SourceRoot=Split-Path -Parent $MyInvocation.MyCommand.Path}
if([string]::IsNullOrWhiteSpace($SourceRoot)){throw "SOURCE PATH ERROR"}
Write-Host "=== V141.01-V145.64 WEB CONTROLLER FOUNDATION FIXED V2 ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
 Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/5] INSTALL CHECK"
python tools\install_check_v141_01_to_v145_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/5] TEST"
python -m unittest tools.test_v141_01_to_v145_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/5] VERIFY"
python tools\verify_v141_01_to_v145_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[4/5] GIT COMMIT"
git add web_controller tools/run_v141_01_to_v145_64.py `
 tools/test_v141_01_to_v145_64.py tools/install_check_v141_01_to_v145_64.py `
 tools/verify_v141_01_to_v145_64.py `
 RUN_V141_01_TO_V145_64_WEB_CONTROLLER.ps1 `
 RUN_V141_01_TO_V145_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V141_01_TO_V145_64_ONE_CLICK.ps1 `
 release/v141_01_to_v145_64 V141_01_TO_V145_64_MANIFEST.json `
 GIT_COMMIT_V141_01_TO_V145_64.txt `
 GIT_COMMIT_V141_01_TO_V145_64_FIXED_V2.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V141.01-V145.64 fix web controller verification import path"}
Write-Host "[5/5] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V141.01-V145.64 FIXED V2 ONE-CLICK COMPLETE"
Write-Host "Start with: .\RUN_V141_01_TO_V145_64_WEB_CONTROLLER.ps1"
