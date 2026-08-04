$names=@("AI Stock Bot Web Controller","AI Stock Bot Pre Market","AI Stock Bot Paper Shadow","AI Stock Bot Post Market")
foreach($name in $names){
 if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){
   Unregister-ScheduledTask -TaskName $name -Confirm:$false
   Write-Host "REMOVED: $name"
 }
}
