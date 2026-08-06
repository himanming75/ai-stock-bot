param([string]$RuntimeRoot="release")
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\runtime_cleanup_v6801.py `
    --root $RuntimeRoot

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "CLEANUP DRY RUN COMPLETE"
Write-Host "NO FILES WERE DELETED OR COMPRESSED"
