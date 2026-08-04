$names=@(
"AI Stock Bot Pre Market",
"AI Stock Bot Market Health",
"AI Stock Bot Qualification",
"AI Stock Bot Portfolio Refresh",
"AI Stock Bot Post Market Report",
"AI Stock Bot Nightly Backup"
)
foreach($name in $names){
  if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "REMOVED: $name"
  }
}
