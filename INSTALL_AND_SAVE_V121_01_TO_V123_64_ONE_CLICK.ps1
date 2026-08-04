param(
[string]$ProjectPath="C:\stock-bot",
[switch]$SkipPush
)
$ErrorActionPreference="Stop"
$SourceRoot=$PSScriptRoot
if([string]::IsNullOrWhiteSpace($SourceRoot)){
 $ScriptFile=$MyInvocation.MyCommand.Path
 if(-not [string]::IsNullOrWhiteSpace($ScriptFile)){
  $SourceRoot=Split-Path -Parent $ScriptFile
 }
}
if([string]::IsNullOrWhiteSpace($SourceRoot)){throw "INSTALL SOURCE PATH COULD NOT BE RESOLVED"}
$SourceRoot=[System.IO.Path]::GetFullPath($SourceRoot)
$ProjectPath=[System.IO.Path]::GetFullPath($ProjectPath)
Write-Host "=== V121.01-V123.64 ALPACA PAPER OPERATIONS FIXED V2 INSTALL ==="
Write-Host "Source:  $SourceRoot"
Write-Host "Project: $ProjectPath"
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
 Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location -LiteralPath $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v121_01_to_v123_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] UNIT TEST"
python -m unittest tools.test_v121_01_to_v123_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] OFFLINE BASE RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V121_01_TO_V123_64.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v121_01_to_v123_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add alpaca_paper_operations tools/run_v121_01_to_v123_64.py `
 tools/test_v121_01_to_v123_64.py tools/install_check_v121_01_to_v123_64.py `
 tools/verify_v121_01_to_v123_64.py RUN_V121_01_TO_V123_64.ps1 `
 RUN_V121_TO_V123_REAL_READ_ONLY.ps1 RUN_V121_TO_V123_SUBMIT_ONE_PAPER_ORDER.ps1 `
 CHECK_V121_ALPACA_PAPER_SETUP.ps1 `
 RUN_V121_01_TO_V123_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V121_01_TO_V123_64_ONE_CLICK.ps1 `
 release/v121_01_to_v123_64 V121_01_TO_V123_64_MANIFEST.json `
 GIT_COMMIT_V121_01_TO_V123_64.txt `
 GIT_COMMIT_V121_01_TO_V123_64_FIXED_V2.txt
$Staged=git diff --cached --name-only
if($Staged){
 git commit -m "V121.01-V123.64 fix Alpaca Paper runtime authorization scripts"
 if($LASTEXITCODE-ne 0){throw "COMMIT FAILED"}
}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){
 git push origin main
 if($LASTEXITCODE-ne 0){throw "PUSH FAILED"}
}
git log -1 --oneline
Write-Host "V121.01-V123.64 FIXED V2 ONE-CLICK COMPLETE"
Write-Host "Real network and Paper order submission remain disabled by default."
