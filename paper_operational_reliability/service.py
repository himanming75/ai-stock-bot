from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonl_health(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "records": 0, "malformed_lines": []}
    records = 0
    malformed = []
    try:
        for idx, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                json.loads(raw)
                records += 1
            except Exception:
                malformed.append(idx)
    except Exception:
        return {"exists": True, "records": 0, "malformed_lines": ["READ_ERROR"]}
    return {"exists": True, "records": records, "malformed_lines": malformed}


def _ps_json(script: str) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
            errors="replace",
        )
        if cp.returncode == 0 and cp.stdout.strip():
            value = json.loads(cp.stdout.strip())
            return value if isinstance(value, dict) else {}
    except Exception:
        pass
    return {}


class OperationalReliabilityService:
    PAPER_TASK = "AIStockBot-PaperAutonomousDailySession"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.runtime = self.root / "runtime"
        self.out = self.runtime / "paper_operational_reliability_v2"
        self.out.mkdir(parents=True, exist_ok=True)

    def task_status(self) -> dict[str, Any]:
        script = (
            f"$t=Get-ScheduledTask -TaskName '{self.PAPER_TASK}' -ErrorAction SilentlyContinue;"
            f"$i=Get-ScheduledTaskInfo -TaskName '{self.PAPER_TASK}' -ErrorAction SilentlyContinue;"
            "if($t){[pscustomobject]@{TaskName=$t.TaskName;State=[string]$t.State;"
            "LastRunTime=[string]$i.LastRunTime;LastTaskResult=$i.LastTaskResult;"
            "NextRunTime=[string]$i.NextRunTime}|ConvertTo-Json -Compress}"
        )
        value = _ps_json(script)
        return value or {"TaskName": self.PAPER_TASK, "State": "UNKNOWN"}

    def process_status(self) -> dict[str, Any]:
        # Exclude the PowerShell process executing this query ($PID).
        # Match only the actual runner script/process signatures.
        root = str(self.root).replace("\\", "\\\\")
        script = (
            "$me=$PID;"
            "$p=Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
            "Where-Object {"
            "$_.ProcessId -ne $me -and ("
            "($_.Name -match '^python(\\.exe)?$' -and $_.CommandLine -match 'run_paper_autonomous_daily_session\\.py') -or "
            f"($_.Name -match '^powershell(\\.exe)?$' -and $_.CommandLine -match '-File\\s+\"?{root}\\\\RUN_PAPER_AUTONOMOUS_DAILY_SESSION\\.ps1')"
            ")} | Select-Object ProcessId,Name,CommandLine;"
            "[pscustomobject]@{Count=@($p).Count;Processes=@($p)}|ConvertTo-Json -Depth 5 -Compress"
        )
        value = _ps_json(script)
        return value or {"Count": 0, "Processes": []}

    def lock_status(self) -> dict[str, Any]:
        paths = [
            self.runtime / "paper_autonomous_daily_session/session.lock",
            self.runtime / "market_open_auto_validation/runner.lock",
        ]
        now = datetime.now(timezone.utc)
        rows = []
        for path in paths:
            exists = path.exists()
            age = None
            if exists:
                try:
                    m = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                    age = max(0.0, (now - m).total_seconds())
                except Exception:
                    pass
            rows.append({
                "path": str(path),
                "exists": exists,
                "age_seconds": round(age, 2) if age is not None else None,
                "stale_candidate": bool(exists and age is not None and age > 900),
            })
        return {
            "locks": rows,
            "stale_candidate_count": sum(1 for x in rows if x["stale_candidate"]),
            "automatic_lock_deletion": False,
        }

    def broker_read_only(self) -> dict[str, Any]:
        key = os.getenv("APCA_API_KEY_ID") or ""
        secret = os.getenv("APCA_API_SECRET_KEY") or ""
        if not key or not secret:
            return {
                "status": "NO_CREDENTIALS_IN_PROCESS",
                "paper_only": True,
                "broker_write_performed": False,
            }
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.enums import QueryOrderStatus
            from alpaca.trading.requests import GetOrdersRequest
            client = TradingClient(key, secret, paper=True)
            clock = client.get_clock()
            account = client.get_account()
            positions = list(client.get_all_positions())
            orders = list(client.get_orders(
                filter=GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=500)
            ))
            return {
                "status": "PASS",
                "paper_only": True,
                "broker_write_performed": False,
                "market_open": bool(getattr(clock, "is_open", False)),
                "next_open": str(getattr(clock, "next_open", "")),
                "next_close": str(getattr(clock, "next_close", "")),
                "account_status": str(getattr(account, "status", "")),
                "trading_blocked": bool(getattr(account, "trading_blocked", False)),
                "position_count": len(positions),
                "position_symbols": sorted(
                    str(getattr(x, "symbol", "")).upper()
                    for x in positions if getattr(x, "symbol", None)
                ),
                "open_order_count": len(orders),
                "open_order_symbols": sorted(
                    str(getattr(x, "symbol", "")).upper()
                    for x in orders if getattr(x, "symbol", None)
                ),
            }
        except Exception as exc:
            return {
                "status": "ERROR",
                "paper_only": True,
                "broker_write_performed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def ledger_health(self) -> dict[str, Any]:
        paths = [
            self.runtime / "paper_full_auto_lifecycle/closed_round_trips.jsonl",
            self.runtime / "paper_full_auto_lifecycle/exit_ledger.jsonl",
            self.runtime / "paper_autotrading_ramp_v2/launch_ledger.jsonl",
            self.runtime / "data_integrity_v61_v65/data_integrity_ledger.jsonl",
            self.runtime / "market_regime_v66_v70/market_regime_ledger.jsonl",
        ]
        rows = []
        malformed_total = 0
        for path in paths:
            h = _jsonl_health(path)
            h["path"] = str(path)
            rows.append(h)
            malformed_total += len(h.get("malformed_lines") or [])
        return {"ledgers": rows, "malformed_total": malformed_total, "automatic_repair": False}

    def recovery_decision(self, task, process, locks, broker) -> dict[str, Any]:
        state = str(task.get("State", "")).upper()
        process_count = int(process.get("Count", 0) or 0)
        stale_locks = int(locks.get("stale_candidate_count", 0) or 0)
        market_open = broker.get("market_open") is True

        reasons = []
        safe = True
        if not market_open:
            safe = False
            reasons.append("MARKET_NOT_OPEN")
        if state == "RUNNING" or process_count > 0:
            safe = False
            reasons.append("SESSION_ALREADY_RUNNING")
        if stale_locks > 0:
            safe = False
            reasons.append("STALE_LOCK_REQUIRES_REVIEW")
        if broker.get("status") != "PASS":
            safe = False
            reasons.append("BROKER_READ_NOT_HEALTHY")
        if broker.get("trading_blocked") is True:
            safe = False
            reasons.append("PAPER_ACCOUNT_TRADING_BLOCKED")

        return {
            "safe_to_restart_task": safe,
            "automatic_restart_performed": False,
            "decision": "RESTART_ELIGIBLE" if safe else "NO_RESTART",
            "reasons": reasons,
            "open_orders_observed": broker.get("open_order_count"),
            "positions_observed": broker.get("position_count"),
        }

    def build(self) -> dict[str, Any]:
        task = self.task_status()
        process = self.process_status()
        locks = self.lock_status()
        broker = self.broker_read_only()
        ledgers = self.ledger_health()
        recovery = self.recovery_decision(task, process, locks, broker)

        checks = {
            "paper_task_exists": task.get("State") != "UNKNOWN",
            "no_duplicate_processes": int(process.get("Count", 0) or 0) <= 1,
            "no_stale_locks": locks["stale_candidate_count"] == 0,
            "broker_read_not_error": broker.get("status") != "ERROR",
            "paper_only_confirmed": broker.get("paper_only", True) is True,
            "ledger_malformed_zero": ledgers["malformed_total"] == 0,
            "broker_write_off": True,
            "automatic_lock_delete_off": True,
        }
        passed = sum(bool(v) for v in checks.values())
        score = round(passed / len(checks) * 100, 2)
        issues = [k for k, v in checks.items() if not v]
        status = "HEALTHY" if not issues else ("WARN" if score >= 75 else "DEGRADED")

        report = {
            "stage": "PAPER_OPERATIONAL_RELIABILITY_V2_1",
            "status": "PASS",
            "mode": "READ_ONLY_OBSERVABILITY_AND_RECOVERY_DECISION",
            "generated_at_utc": _now(),
            "broker_write_performed": False,
            "trading_configuration_changed": False,
            "automatic_repair_performed": False,
            "task": task,
            "process": process,
            "locks": locks,
            "broker": broker,
            "ledger_health": ledgers,
            "recovery_decision": recovery,
            "health": {
                "status": status,
                "score": score,
                "passed_checks": passed,
                "total_checks": len(checks),
                "checks": checks,
                "issues": issues,
            },
        }
        (self.out / "latest_operational_reliability_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        with (self.out / "operational_reliability_ledger.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False, sort_keys=True, default=str) + "\n")
        return report
