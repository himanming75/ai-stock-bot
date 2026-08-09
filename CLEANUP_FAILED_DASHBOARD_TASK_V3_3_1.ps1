$ErrorActionPreference="SilentlyContinue"

$TaskName="AIStockBot-OperationsDashboard-V3_3"

Write-Host "=== OPTIONAL FAILED TASK CLEANUP ==="

$Task=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if($Task){
    try{
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "PARTIAL/OLD TASK REMOVED: $TaskName"
    }catch{
        Write-Host "TASK CLEANUP SKIPPED: no permission"
    }
}else{
    Write-Host "NO EXISTING DASHBOARD TASK TO REMOVE"
}

exit 0
