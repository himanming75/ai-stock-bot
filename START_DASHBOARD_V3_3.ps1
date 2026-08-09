$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"
$Server="$Repo\dashboard\operations_dashboard_v3_2.py"

Set-Location $Repo

$Existing=@(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
)

if($Existing.Count -gt 0){
    try{
        $Page=Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 3
        if($Page.Content -match "AI Stock Bot Unified Operations Dashboard"){
            Write-Host "V3 dashboard already running on port $Port."
            exit 0
        }
    }catch{}

    Write-Host "PORT $Port occupied by non-V3 process."
    $Existing | Format-Table LocalAddress,LocalPort,State,OwningProcess -AutoSize
    exit 2
}

if(-not(Test-Path $Python)){throw "PYTHON NOT FOUND: $Python"}
if(-not(Test-Path $Server)){throw "SERVER NOT FOUND: $Server"}

& $Python $Server --root $Repo --host 127.0.0.1 --port $Port
