param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)
$ErrorActionPreference = "Stop"

$SourceRoot = $PSScriptRoot
if([string]::IsNullOrWhiteSpace($SourceRoot)){
    $ScriptFile = $MyInvocation.MyCommand.Path
    if(-not [string]::IsNullOrWhiteSpace($ScriptFile)){
        $SourceRoot = Split-Path -Parent $ScriptFile
    }
}
if([string]::IsNullOrWhiteSpace($SourceRoot)){
    throw "INSTALL SOURCE PATH COULD NOT BE RESOLVED"
}

$SourceRoot = [System.IO.Path]::GetFullPath($SourceRoot)
$ProjectPath = [System.IO.Path]::GetFullPath($ProjectPath)

Write-Host "=== V106.01-V106.32 DAILY PAPER RUNNER ONE-CLICK INSTALL ==="
Write-Host "Source:  $SourceRoot"
Write-Host "Project: $ProjectPath"

Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
    Copy-Item `
        -LiteralPath $_.FullName `
        -Destination $ProjectPath `
        -Recurse `
        -Force
}

Set-Location -LiteralPath $ProjectPath

Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v106_01_to_v106_32.py
if($LASTEXITCODE -ne 0){throw "INSTALL FAILED"}

Write-Host "[2/6] UNIT TEST"
python -m unittest tools.test_v106_01_to_v106_32 -v
if($LASTEXITCODE -ne 0){throw "TEST FAILED"}

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
    -File .\RUN_V106_01_TO_V106_32.ps1
if($LASTEXITCODE -ne 0){throw "RUN FAILED"}

Write-Host "[4/6] VERIFY"
python tools\verify_v106_01_to_v106_32.py
if($LASTEXITCODE -ne 0){throw "VERIFY FAILED"}

Write-Host "[5/6] GIT COMMIT"
git add `
    daily_paper_runner `
    tools/run_v106_01_to_v106_32.py `
    tools/test_v106_01_to_v106_32.py `
    tools/install_check_v106_01_to_v106_32.py `
    tools/verify_v106_01_to_v106_32.py `
    RUN_V106_01_TO_V106_32.ps1 `
    RUN_V106_01_TO_V106_32_TEST_AND_VERIFY.ps1 `
    INSTALL_AND_SAVE_V106_01_TO_V106_32_ONE_CLICK.ps1 `
    release/v106_01_to_v106_32 `
    V106_01_TO_V106_32_MANIFEST.json `
    GIT_COMMIT_V106_01_TO_V106_32.txt

$StagedFiles = git diff --cached --name-only
if($StagedFiles){
    git commit -m "V106.01-V106.32 daily autonomous paper trading runner integrated"
    if($LASTEXITCODE -ne 0){throw "COMMIT FAILED"}
}

Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){
    git push origin main
    if($LASTEXITCODE -ne 0){throw "PUSH FAILED"}
}

git log -1 --oneline
Write-Host "V106.01-V106.32 ONE-CLICK COMPLETE"
