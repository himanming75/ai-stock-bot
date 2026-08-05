param(
    [switch]$Once,
    [ValidateRange(5, 3600)]
    [int]$RefreshSeconds = 30
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# When copied to C:\stock-bot, this resolves directly.
# When run from the ZIP folder, allow the current working directory to be the project root.
if (-not (Test-Path (Join-Path $ProjectRoot "RUN_V321_01_TO_V330_64_ANALYZE.ps1"))) {
    $ProjectRoot = (Get-Location).Path
}

$AnalyzeScript = Join-Path $ProjectRoot "RUN_V321_01_TO_V330_64_ANALYZE.ps1"
if (-not (Test-Path $AnalyzeScript)) {
    Write-Host ""
    Write-Host "ERROR: Analyze script not found:" -ForegroundColor Red
    Write-Host $AnalyzeScript -ForegroundColor Red
    Write-Host ""
    Write-Host "Run this monitor from C:\stock-bot or copy it into C:\stock-bot."
    exit 1
}

function Get-V330Analysis {
    $raw = & $AnalyzeScript 2>&1 | Out-String
    try {
        return $raw | ConvertFrom-Json
    }
    catch {
        Write-Host ""
        Write-Host "Unable to parse V330 analysis output." -ForegroundColor Red
        Write-Host $raw
        throw
    }
}

function Format-Duration([double]$Minutes) {
    if ($Minutes -lt 0) { $Minutes = 0 }
    $span = [TimeSpan]::FromMinutes($Minutes)
    if ($span.TotalHours -ge 1) {
        return ("{0}h {1}m" -f [math]::Floor($span.TotalHours), $span.Minutes)
    }
    return ("{0}m {1}s" -f $span.Minutes, $span.Seconds)
}

function Show-V330Status {
    $result = Get-V330Analysis
    $stats = $result.statistics
    $checks = $result.checks

    $minimumCycles = 120
    $minimumMinutes = 60.0

    $successful = [int]$stats.successful_cycles
    $total = [int]$stats.total_cycles
    $blocked = [int]$stats.blocked_cycles
    $errors = [int]$stats.error_records
    $observedMinutes = [double]$stats.observation_minutes
    $successRatio = [double]$stats.success_ratio

    $remainingCycles = [math]::Max(0, $minimumCycles - $successful)
    $remainingMinutesByTime = [math]::Max(0.0, $minimumMinutes - $observedMinutes)

    $avgCycleSeconds = 30.0
    if ($total -gt 1 -and $observedMinutes -gt 0) {
        $avgCycleSeconds = ($observedMinutes * 60.0) / ($total - 1)
    }

    $remainingMinutesByCycles = ($remainingCycles * $avgCycleSeconds) / 60.0
    $estimatedRemainingMinutes = [math]::Max(
        $remainingMinutesByTime,
        $remainingMinutesByCycles
    )

    $cyclePercent = [math]::Min(100.0, ($successful / $minimumCycles) * 100.0)
    $timePercent = [math]::Min(100.0, ($observedMinutes / $minimumMinutes) * 100.0)
    $overallPercent = [math]::Min($cyclePercent, $timePercent)

    Clear-Host
    Write-Host "============================================================"
    Write-Host " V330.64 REAL PAPER LONG-RUN QUALIFICATION MONITOR"
    Write-Host "============================================================"
    Write-Host ("Updated:               {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
    Write-Host ("State:                 {0}" -f $result.state)
    Write-Host ("Status:                {0}" -f $result.status)
    Write-Host ""
    Write-Host ("Successful cycles:     {0} / {1}" -f $successful, $minimumCycles)
    Write-Host ("Total cycles:          {0}" -f $total)
    Write-Host ("Remaining cycles:      {0}" -f $remainingCycles)
    Write-Host ("Observation time:      {0:N3} / {1} minutes" -f $observedMinutes, $minimumMinutes)
    Write-Host ("Success ratio:         {0:P2}" -f $successRatio)
    Write-Host ("Blocked cycles:        {0}" -f $blocked)
    Write-Host ("Error records:         {0}" -f $errors)
    Write-Host ("Overall progress:      {0:N1}%%" -f $overallPercent)
    Write-Host ("Estimated time left:   {0}" -f (Format-Duration $estimatedRemainingMinutes))
    Write-Host ""
    Write-Host "Safety"
    Write-Host ("  Paper orders:        {0}" -f $result.actual_paper_orders_submitted)
    Write-Host ("  Live orders:         {0}" -f $result.actual_live_orders_submitted)
    Write-Host ("  Broker write OFF:    {0}" -f $checks.broker_write_disabled)
    Write-Host ("  Paper submit OFF:    {0}" -f $checks.paper_submission_disabled)
    Write-Host ("  Live submit OFF:     {0}" -f $checks.live_submission_disabled)
    Write-Host ""

    if ($result.state -eq "REAL_PAPER_LONG_RUN_QUALIFIED") {
        Write-Host "QUALIFICATION COMPLETE" -ForegroundColor Green
        Write-Host "V331 implementation may now proceed." -ForegroundColor Green
        return $true
    }

    if ($blocked -gt 0 -or $errors -gt 0 -or $checks.corrupt_records_zero -ne $true) {
        Write-Host "ATTENTION REQUIRED" -ForegroundColor Yellow
        Write-Host "Review blocked cycles, errors, or ledger integrity." -ForegroundColor Yellow
    }
    else {
        Write-Host "NORMAL: Qualification is still collecting data." -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host ("Next refresh in {0} seconds. Press Ctrl+C to stop this monitor." -f $RefreshSeconds)
    return $false
}

do {
    $complete = Show-V330Status
    if ($Once -or $complete) {
        break
    }
    Start-Sleep -Seconds $RefreshSeconds
} while ($true)
