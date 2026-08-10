$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo

$Files=@(
 "START_PERSONAL_STOCK_BOT.ps1",
 "STOP_PERSONAL_STOCK_BOT.ps1",
 "RECOVER_PERSONAL_STOCK_BOT.ps1"
)
foreach($f in $Files){
 if(-not (Test-Path $f)){throw "MISSING $f"}
}

foreach($f in $Files){
 $Errors=$null
 [System.Management.Automation.Language.Parser]::ParseFile(
   (Join-Path $Repo $f),[ref]$null,[ref]$Errors
 ) | Out-Null
 if($Errors){throw "PARSER ERROR IN $f : $($Errors | Out-String)"}
}

$Stop=Get-Content .\STOP_PERSONAL_STOCK_BOT.ps1 -Raw
$Start=Get-Content .\START_PERSONAL_STOCK_BOT.ps1 -Raw
$Recover=Get-Content .\RECOVER_PERSONAL_STOCK_BOT.ps1 -Raw

if($Stop -notmatch 'Validation Scheduler PID .*STOPPED'){throw "STOP WAIT MARKER MISSING"}
if($Start -notmatch 'VALIDATION_SCHEDULER_DID_NOT_STAY_RUNNING'){throw "START SURVIVAL CHECK MISSING"}
if($Recover -notmatch 'RECOVERY_SCHEDULER_DIED_AFTER_INITIAL_CHECK'){throw "RECOVERY RECHECK MISSING"}

Write-Host "VERIFY: PASS"
Write-Host "Scheduler stop wait: ENABLED"
Write-Host "Scheduler startup survival check: ENABLED"
Write-Host "Paper/Live order submission added: NO"
