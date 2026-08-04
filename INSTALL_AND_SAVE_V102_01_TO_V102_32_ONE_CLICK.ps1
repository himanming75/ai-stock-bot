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

if(-not (Test-Path -LiteralPath $ProjectPath)){
    New-Item -ItemType Directory -Path $ProjectPath -Force | Out-Null
}

Write-Host "=== V102.01-V102.32 ONE-CLICK INSTALL ==="
Write-Host "Source:  $SourceRoot"
Write-Host "Project: $ProjectPath"

Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}

Set-Location -LiteralPath $ProjectPath

Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v102_01_to_v102_32.py
if($LASTEXITCODE -ne 0){throw "INSTALL FAILED"}

Write-Host "[2/6] UNIT TEST"
python -m unittest tools.test_v102_01_to_v102_32 -v
if($LASTEXITCODE -ne 0){throw "TEST FAILED"}

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V102_01_TO_V102_32.ps1
if($LASTEXITCODE -ne 0){throw "RUN FAILED"}

Write-Host "[4/6] VERIFY"
python tools\verify_v102_01_to_v102_32.py
if($LASTEXITCODE -ne 0){throw "VERIFY FAILED"}

Write-Host "[5/6] GIT COMMIT"
git add `
    master_ai_orchestrator `
    tools/run_v102_01_to_v102_32.py `
    tools/test_v102_01_to_v102_32.py `
    tools/install_check_v102_01_to_v102_32.py `
    tools/verify_v102_01_to_v102_32.py `
    RUN_V102_01_TO_V102_32.ps1 `
    RUN_V102_01_TO_V102_32_TEST_AND_VERIFY.ps1 `
    INSTALL_AND_SAVE_V102_01_TO_V102_32_ONE_CLICK.ps1 `
    release/v102_01_to_v102_32 `
    V102_01_TO_V102_32_MANIFEST.json `
    GIT_COMMIT_V102_01_TO_V102_32.txt

$StagedFiles = git diff --cached --name-only
if($StagedFiles){
    git commit -m "V102.01-V102.32 master AI orchestrator core integrated"
    if($LASTEXITCODE -ne 0){throw "COMMIT FAILED"}
}

Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){
    git push origin main
    if($LASTEXITCODE -ne 0){throw "PUSH FAILED"}
}
git log -1 --oneline
Write-Host "V102.01-V102.32 ONE-CLICK COMPLETE"
