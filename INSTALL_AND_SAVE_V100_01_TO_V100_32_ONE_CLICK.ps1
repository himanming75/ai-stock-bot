param(
    [string]$ProjectPath = "C:\stock-bot",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

# Resolve the folder that contains this installer.
$SourceRoot = $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    $ScriptFile = $MyInvocation.MyCommand.Path

    if (-not [string]::IsNullOrWhiteSpace($ScriptFile)) {
        $SourceRoot = Split-Path -Parent $ScriptFile
    }
}

if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    throw "INSTALL SOURCE PATH COULD NOT BE RESOLVED. Run this file with: powershell -ExecutionPolicy Bypass -File <full path to this ps1>"
}

$SourceRoot = [System.IO.Path]::GetFullPath($SourceRoot)
$ProjectPath = [System.IO.Path]::GetFullPath($ProjectPath)

if (-not (Test-Path -LiteralPath $SourceRoot)) {
    throw "INSTALL SOURCE NOT FOUND: $SourceRoot"
}

if (-not (Test-Path -LiteralPath $ProjectPath)) {
    New-Item -ItemType Directory -Path $ProjectPath -Force | Out-Null
}

Write-Host "=== V100.01-V100.32 FIXED V2 ONE-CLICK INSTALL ==="
Write-Host "Source:  $SourceRoot"
Write-Host "Project: $ProjectPath"

# Copy every package item except the temporary extraction directory itself.
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
    Copy-Item `
        -LiteralPath $_.FullName `
        -Destination $ProjectPath `
        -Recurse `
        -Force
}

Set-Location -LiteralPath $ProjectPath

Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v100_01_to_v100_32.py
if ($LASTEXITCODE -ne 0) {
    throw "INSTALL FAILED"
}

Write-Host "[2/6] UNIT TEST"
python -m unittest tools.test_v100_01_to_v100_32 -v
if ($LASTEXITCODE -ne 0) {
    throw "TEST FAILED"
}

Write-Host "[3/6] BASE RUN"
powershell -ExecutionPolicy Bypass `
    -File .\RUN_V100_01_TO_V100_32.ps1
if ($LASTEXITCODE -ne 0) {
    throw "RUN FAILED"
}

Write-Host "[4/6] VERIFY"
python tools\verify_v100_01_to_v100_32.py
if ($LASTEXITCODE -ne 0) {
    throw "VERIFY FAILED"
}

Write-Host "[5/6] GIT COMMIT"
git add `
    ai_risk_manager `
    tools/run_v100_01_to_v100_32.py `
    tools/test_v100_01_to_v100_32.py `
    tools/install_check_v100_01_to_v100_32.py `
    tools/verify_v100_01_to_v100_32.py `
    RUN_V100_01_TO_V100_32.ps1 `
    RUN_V100_01_TO_V100_32_TEST_AND_VERIFY.ps1 `
    INSTALL_AND_SAVE_V100_01_TO_V100_32_ONE_CLICK.ps1 `
    release/v100_01_to_v100_32 `
    V100_01_TO_V100_32_MANIFEST.json `
    GIT_COMMIT_V100_01_TO_V100_32.txt `
    GIT_COMMIT_V100_01_TO_V100_32_FIXED.txt `
    GIT_COMMIT_V100_01_TO_V100_32_FIXED_V2.txt

$StagedFiles = git diff --cached --name-only

if ($StagedFiles) {
    git commit -m "V100.01-V100.32 harden one-click installer source path resolution"
    if ($LASTEXITCODE -ne 0) {
        throw "COMMIT FAILED"
    }
}
else {
    Write-Host "No new Git changes to commit."
}

Write-Host "[6/6] GIT PUSH"
if (-not $SkipPush) {
    git push origin main
    if ($LASTEXITCODE -ne 0) {
        throw "PUSH FAILED"
    }
}

git log -1 --oneline
Write-Host "V100.01-V100.32 FIXED V2 ONE-CLICK COMPLETE"
