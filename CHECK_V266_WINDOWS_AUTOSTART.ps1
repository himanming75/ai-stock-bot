$task = Get-ScheduledTask -TaskName "AIStockBot-AutonomousPaper" -ErrorAction SilentlyContinue
if($null -eq $task){
  Write-Host "Autostart task is NOT registered."
} else {
  $task | Select-Object TaskName,State | Format-Table -AutoSize
}
