$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8879

Write-Host "=== V3.9 DIRECT SERVER VERIFY ==="

$Existing=@(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
)
foreach($L in $Existing){
    Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
}

$P=Start-Process `
    -FilePath $Python `
    -ArgumentList @(
        "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
        "--root","C:\stock-bot",
        "--host","127.0.0.1",
        "--port","$Port"
    ) `
    -WorkingDirectory "C:\stock-bot" `
    -PassThru

try{
    Start-Sleep -Seconds 5

    $S=Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/status" `
        -TimeoutSec 20

    $HTML=(Invoke-WebRequest `
        -UseBasicParsing `
        -Uri "http://127.0.0.1:$Port/" `
        -TimeoutSec 20).Content

    $Pfm=$S.performance
    $Hist=$S.trade_analytics.historical
    $Viz=$S.visualization

    Write-Host "VISUALIZATION STATUS:" $S.visualization_status
    Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
    Write-Host "CANONICAL STATUS:" $S.trade_analytics.canonical_lifecycle_discovery.status
    Write-Host "TOP HISTORICAL CLOSED TRADES:" $Pfm.historical_closed_trades
    Write-Host "ANALYTICS NUMERIC TRADES:" $Hist.numeric_trade_count
    Write-Host "TOP REALIZED PNL:" $Pfm.historical_realized_pnl
    Write-Host "ANALYTICS REALIZED PNL:" $Hist.net_realized_pnl
    Write-Host "TOP WIN RATE:" $Pfm.win_rate
    Write-Host "ANALYTICS WIN RATE:" $Hist.win_rate
    Write-Host "TOP PROFIT FACTOR:" $Pfm.profit_factor
    Write-Host "ANALYTICS PROFIT FACTOR:" $Hist.profit_factor
    Write-Host "DAILY PNL POINTS:" $Viz.summary.daily_realized_point_count
    Write-Host "DAILY PNL ROWS:" $Viz.daily_realized_pnl.Count

    $KoreanOK=(
        $HTML.Contains("시스템 상태") -and
        $HTML.Contains("계좌 평가금액") -and
        $HTML.Contains("현재 보유 포지션") -and
        $HTML.Contains("일별 실현손익") -and
        $HTML.Contains("누적 성과 및 거래 분석")
    )

    Write-Host "KOREAN BILINGUAL UI:" $KoreanOK

    if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
    if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
    if($Pfm.historical_closed_trades -ne $Hist.numeric_trade_count){throw "CLOSED TRADE COUNT NOT UNIFIED"}

    if([math]::Abs([double]$Pfm.historical_realized_pnl-[double]$Hist.net_realized_pnl) -gt 0.00000001){
        throw "REALIZED PNL NOT UNIFIED"
    }

    if([math]::Abs([double]$Pfm.win_rate-[double]$Hist.win_rate) -gt 0.00000001){
        throw "WIN RATE NOT UNIFIED"
    }

    if(-not $KoreanOK){throw "BILINGUAL UI VERIFY FAILED"}

    if($Hist.numeric_trade_count -gt 0 -and $Viz.summary.daily_realized_point_count -lt 1){
        throw "CANONICAL DAILY PNL CHART NOT POPULATED"
    }

    Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
    Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
