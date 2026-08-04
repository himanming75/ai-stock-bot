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
Write-Host "=== V120 FINAL PRODUCTION RELEASE ONE-CLICK INSTALL ==="
Write-Host "Source:  $SourceRoot"
Write-Host "Project: $ProjectPath"
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
 Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location -LiteralPath $ProjectPath
Write-Host "[1/7] INSTALL CHECK"
python tools\install_check_v120_final.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/7] UNIT TEST"
python -m unittest tools.test_v120_final -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/7] FINAL BUILD"
powershell -ExecutionPolicy Bypass -File .\RUN_V120_FINAL.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/7] VERIFY"
python tools\verify_v120_final.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/7] GIT COMMIT"
git add v120_final_release tools/run_v120_final.py tools/test_v120_final.py `
 tools/install_check_v120_final.py tools/verify_v120_final.py `
 RUN_V120_FINAL.ps1 RUN_V120_FINAL_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V120_FINAL_ONE_CLICK.ps1 release/v120_final `
 V120_FINAL_MANIFEST.json GIT_COMMIT_V120_FINAL.txt
$Staged=git diff --cached --name-only
if($Staged){
 git commit -m "V120 final production release integrated"
 if($LASTEXITCODE-ne 0){throw "COMMIT FAILED"}
}
Write-Host "[6/7] GIT TAG"
$Tag="v120.0-final"
if(-not (git tag --list $Tag)){
 git tag -a $Tag -m "AI Stock Bot V120 Final Development Release"
 if($LASTEXITCODE-ne 0){throw "TAG FAILED"}
}
Write-Host "[7/7] GIT PUSH"
if(-not $SkipPush){
 git push origin main
 if($LASTEXITCODE-ne 0){throw "PUSH FAILED"}
 git push origin $Tag
 if($LASTEXITCODE-ne 0){throw "TAG PUSH FAILED"}
}
git log -1 --oneline
Write-Host "V120 FINAL ONE-CLICK COMPLETE"
