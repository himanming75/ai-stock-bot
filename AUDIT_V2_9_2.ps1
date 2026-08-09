$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$OutDir = "C:\stock-bot\runtime\regime_aware_buy_shadow_v2_9_2"
New-Item -ItemType Directory -Force $OutDir | Out-Null

$ExpectedRepo = "C:\stock-bot"
$ExpectedRunner = "RUN_PAPER_AUTONOMOUS_DAILY_SESSION.ps1"
$LockPath = "C:\stock-bot\runtime\paper_autonomous_daily_session\session.lock"
$StopPath = "C:\stock-bot\runtime\paper_autonomous_daily_session\STOP"
$HookLedger = "C:\stock-bot\runtime\regime_aware_buy_shadow_v2_8_1\hook_ledger.jsonl"
$ShadowLedger = "C:\stock-bot\runtime\regime_aware_buy_shadow_v2_7\shadow_candidate_ledger.jsonl"
$CertReport = "C:\stock-bot\runtime\regime_aware_buy_shadow_v2_9\latest_runtime_shadow_certification_v2_9.json"

function Convert-TaskActionText($Task) {
    $Parts = @()
    foreach($Action in @($Task.Actions)) {
        $Parts += (($Action.Execute, $Action.Arguments, $Action.WorkingDirectory) -join " ")
    }
    return ($Parts -join " | ")
}

Write-Host "=== V2.9.2 SCHEDULED TASK / RUNTIME ACTIVATION AUDIT ==="

$AllTasks = @(Get-ScheduledTask -ErrorAction Stop)
$Candidates = @()

foreach($Task in $AllTasks) {
    $ActionText = Convert-TaskActionText $Task

    $Score = 0
    $Reasons = @()

    if($Task.TaskName -match "AIStockBot|StockBot") {
        $Score += 4
        $Reasons += "TASK_NAME_STOCKBOT"
    }
    if($Task.TaskName -match "Paper") {
        $Score += 3
        $Reasons += "TASK_NAME_PAPER"
    }
    if($ActionText -match [regex]::Escape($ExpectedRunner)) {
        $Score += 10
        $Reasons += "EXACT_DAILY_SESSION_RUNNER"
    }
    if($ActionText -match [regex]::Escape($ExpectedRepo)) {
        $Score += 4
        $Reasons += "EXPECTED_REPO"
    }
    if($ActionText -match "paper_autonomous_daily_session|PaperAutonomousDailySession") {
        $Score += 5
        $Reasons += "DAILY_SESSION_TEXT"
    }

    if($Score -gt 0) {
        $Info = $null
        try {
            $Info = Get-ScheduledTaskInfo -TaskName $Task.TaskName -TaskPath $Task.TaskPath -ErrorAction Stop
        } catch {}

        $Candidates += [pscustomobject]@{
            TaskName = $Task.TaskName
            TaskPath = $Task.TaskPath
            State = [string]$Task.State
            Score = $Score
            Reasons = $Reasons
            ActionText = $ActionText
            NextRunTime = if($Info){[string]$Info.NextRunTime}else{$null}
            LastRunTime = if($Info){[string]$Info.LastRunTime}else{$null}
            LastTaskResult = if($Info){[string]$Info.LastTaskResult}else{$null}
        }
    }
}

$Candidates = @($Candidates | Sort-Object Score -Descending)

$Exact = @($Candidates | Where-Object { $_.Reasons -contains "EXACT_DAILY_SESSION_RUNNER" })
$Selected = $null
$SelectionStatus = $null

if($Exact.Count -eq 1) {
    $Selected = $Exact[0]
    $SelectionStatus = "EXACT_ACTION_MATCH"
} elseif($Exact.Count -gt 1) {
    $SelectionStatus = "AMBIGUOUS_EXACT_ACTION_MATCH"
} elseif($Candidates.Count -eq 1) {
    $Selected = $Candidates[0]
    $SelectionStatus = "SINGLE_HEURISTIC_MATCH"
} elseif($Candidates.Count -eq 0) {
    $SelectionStatus = "NO_TASK_MATCH"
} else {
    $TopScore = $Candidates[0].Score
    $Top = @($Candidates | Where-Object {$_.Score -eq $TopScore})
    if($Top.Count -eq 1 -and $TopScore -ge 8) {
        $Selected = $Top[0]
        $SelectionStatus = "UNIQUE_HIGH_SCORE_MATCH"
    } else {
        $SelectionStatus = "AMBIGUOUS_TASK_MATCH"
    }
}

$Lock = [ordered]@{
    exists = Test-Path -LiteralPath $LockPath
    pid = $null
    created_at_utc = $null
    pid_alive = $false
    stale = $false
    parse_error = $null
}

if($Lock.exists) {
    try {
        $LockJson = Get-Content $LockPath -Raw | ConvertFrom-Json
        $Lock.pid = $LockJson.pid
        $Lock.created_at_utc = $LockJson.created_at_utc
        if($null -ne $Lock.pid) {
            $Proc = Get-Process -Id ([int]$Lock.pid) -ErrorAction SilentlyContinue
            $Lock.pid_alive = ($null -ne $Proc)
            $Lock.stale = (-not $Lock.pid_alive)
        }
    } catch {
        $Lock.parse_error = $_.Exception.Message
        $Lock.stale = $true
    }
}

$RunnerCompile = $false
$Python = if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
& $Python -m py_compile .\paper_daily_session\runner.py
if($LASTEXITCODE -eq 0) {
    $RunnerCompile = $true
}

$RunnerText = Get-Content ".\paper_daily_session\runner.py" -Raw
$HookMethodCount = ([regex]::Matches($RunnerText, "def _run_regime_shadow_cycle\(self\)")).Count
$HookCallCount = ([regex]::Matches($RunnerText, "regime_shadow_v2_8_1 = self\._run_regime_shadow_cycle\(\)")).Count

$GitHead = (git rev-parse HEAD).Trim()
$GitBranch = (git branch --show-current).Trim()
$OriginMain = ""
try { $OriginMain = (git rev-parse origin/main).Trim() } catch {}

$PreviousCert = $null
if(Test-Path $CertReport) {
    try { $PreviousCert = Get-Content $CertReport -Raw | ConvertFrom-Json } catch {}
}

$TaskReady = $false
$TaskIssues = @()

if($null -eq $Selected) {
    $TaskIssues += $SelectionStatus
} else {
    if($Selected.State -eq "Disabled") {
        $TaskIssues += "TASK_DISABLED"
    }
    if($Selected.ActionText -notmatch [regex]::Escape($ExpectedRepo)) {
        $TaskIssues += "TASK_ACTION_NOT_POINTING_TO_EXPECTED_REPO"
    }
    if($Selected.ActionText -notmatch [regex]::Escape($ExpectedRunner)) {
        $TaskIssues += "TASK_ACTION_NOT_USING_EXPECTED_DAILY_RUNNER"
    }
    if($Selected.State -ne "Disabled" -and
       $Selected.ActionText -match [regex]::Escape($ExpectedRepo) -and
       $Selected.ActionText -match [regex]::Escape($ExpectedRunner)) {
        $TaskReady = $true
    }
}

$RuntimeIssues = @()
if(-not $RunnerCompile){$RuntimeIssues += "RUNNER_COMPILE_FAILED"}
if($HookMethodCount -ne 1){$RuntimeIssues += "HOOK_METHOD_COUNT_INVALID"}
if($HookCallCount -ne 1){$RuntimeIssues += "HOOK_CALL_COUNT_INVALID"}
if($Lock.exists -and $Lock.stale){$RuntimeIssues += "STALE_SESSION_LOCK"}
if($GitBranch -ne "main"){$RuntimeIssues += "NOT_ON_MAIN_BRANCH"}
if($OriginMain -and $GitHead -ne $OriginMain){$RuntimeIssues += "HEAD_NOT_EQUAL_ORIGIN_MAIN"}

$Status = "PASS_RUNTIME_ACTIVATION_READY"
if($TaskIssues.Count -gt 0) {
    $Status = "BLOCKED_SCHEDULED_TASK_CONFIGURATION"
} elseif($RuntimeIssues.Count -gt 0) {
    $Status = "BLOCKED_RUNTIME_ACTIVATION_INTEGRITY"
} elseif($null -ne $PreviousCert -and $PreviousCert.status -eq "PASS_WAITING_FOR_RUNTIME_OBSERVATION") {
    $Status = "PASS_READY_WAITING_FOR_NEXT_SCHEDULED_RUNTIME"
}

$Report = [ordered]@{
    stage = "V2.9.2_SCHEDULED_TASK_RUNTIME_ACTIVATION_AUDIT"
    status = $Status
    generated_at_utc = [DateTime]::UtcNow.ToString("o")
    task_selection = [ordered]@{
        selection_status = $SelectionStatus
        selected = $Selected
        candidate_count = $Candidates.Count
        candidates = $Candidates
        task_ready = $TaskReady
        issues = $TaskIssues
    }
    runtime_integrity = [ordered]@{
        repo = $ExpectedRepo
        branch = $GitBranch
        head = $GitHead
        origin_main = $OriginMain
        head_equals_origin_main = (($OriginMain -ne "") -and ($GitHead -eq $OriginMain))
        runner_compile_pass = $RunnerCompile
        hook_method_count = $HookMethodCount
        hook_call_count = $HookCallCount
        stop_file_exists = (Test-Path -LiteralPath $StopPath)
        lock = $Lock
        hook_ledger_exists = (Test-Path -LiteralPath $HookLedger)
        shadow_ledger_exists = (Test-Path -LiteralPath $ShadowLedger)
        previous_v2_9_status = if($PreviousCert){$PreviousCert.status}else{$null}
        issues = $RuntimeIssues
    }
    activation_contract = [ordered]@{
        scheduled_task_modified = $false
        scheduled_task_started_by_v2_9_2 = $false
        stop_file_removed = $false
        lock_file_removed = $false
        paper_runtime_started_by_v2_9_2 = $false
        broker_write_performed = $false
        paper_order_submission_performed = $false
        live_order_submission_performed = $false
        production_parameter_modified = $false
        production_selector_modified = $false
        network_used = $false
        automatic_promotion = $false
    }
}

$ReportPath = Join-Path $OutDir "latest_runtime_activation_audit_v2_9_2.json"
$Report | ConvertTo-Json -Depth 20 | Set-Content -Path $ReportPath -Encoding UTF8

$Report | ConvertTo-Json -Depth 20

if($Status -like "BLOCKED*") {
    exit 2
}

exit 0
