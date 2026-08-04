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

Write-Host "=== V105.33-V105.64 FINAL RELEASE ONE-CLICK INSTALL ==="
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

Write-Host "[1/7] INSTALL CHECK"
python tools\install_check_v105_33_to_v105_64.py
if($LASTEXITCODE -ne 0){throw "INSTALL FAILED"}

Write-Host "[2/7] UNIT TEST"
python -m unittest tools.test_v105_33_to_v105_64 -v
if($LASTEXITCODE -ne 0){throw "TEST FAILED"}

Write-Host "[3/7] FINAL RELEASE BUILD"
powershell -ExecutionPolicy Bypass `
    -File .\RUN_V105_33_TO_V105_64.ps1
if($LASTEXITCODE -ne 0){throw "RUN FAILED"}

Write-Host "[4/7] VERIFY"
python tools\verify_v105_33_to_v105_64.py
if($LASTEXITCODE -ne 0){throw "VERIFY FAILED"}

Write-Host "[5/7] GIT COMMIT"
git add `
    final_release `
    tools/run_v105_33_to_v105_64.py `
    tools/test_v105_33_to_v105_64.py `
    tools/install_check_v105_33_to_v105_64.py `
    tools/verify_v105_33_to_v105_64.py `
    RUN_V105_33_TO_V105_64.ps1 `
    RUN_V105_33_TO_V105_64_TEST_AND_VERIFY.ps1 `
    INSTALL_AND_SAVE_V105_33_TO_V105_64_ONE_CLICK.ps1 `
    release/v105_33_to_v105_64 `
    V105_33_TO_V105_64_MANIFEST.json `
    GIT_COMMIT_V105_33_TO_V105_64.txt

$StagedFiles = git diff --cached --name-only
if($StagedFiles){
    git commit -m "V105.33-V105.64 production readiness and final release integrated"
    if($LASTEXITCODE -ne 0){throw "COMMIT FAILED"}
}

Write-Host "[6/7] GIT TAG"
$TagName = "v105-final-paper-release"
$ExistingTag = git tag --list $TagName
if(-not $ExistingTag){
    git tag -a $TagName -m "AI Stock Bot V105 Final Paper Trading Release"
    if($LASTEXITCODE -ne 0){throw "TAG FAILED"}
}

Write-Host "[7/7] GIT PUSH"
if(-not $SkipPush){
    git push origin main
    if($LASTEXITCODE -ne 0){throw "PUSH FAILED"}
    git push origin $TagName
    if($LASTEXITCODE -ne 0){throw "TAG PUSH FAILED"}
}

git log -1 --oneline
Write-Host "V105.33-V105.64 FINAL RELEASE ONE-CLICK COMPLETE"
