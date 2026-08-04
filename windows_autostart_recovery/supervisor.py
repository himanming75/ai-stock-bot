from __future__ import annotations
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from windows_autostart_recovery.config import load, validate
from windows_autostart_recovery.io import write_json, append_jsonl
from windows_autostart_recovery.logs import cleanup
from windows_autostart_recovery.recovery import inspect as inspect_recovery
from windows_autostart_recovery.stale_lock import remove_if_stale

def run(root: Path, execute_child: bool = False) -> dict:
    policy = load(root)
    validation = validate(policy)
    lock_path = root / "release/v261_01_to_v265_64/control/session_runner.lock"
    stale = remove_if_stale(lock_path, int(policy["stale_lock_minutes"]))
    recovery = inspect_recovery(root)
    log_cleanup = cleanup(
        root / "release/v266_01_to_v270_64/logs",
        int(policy["log_retention_days"]),
    )

    blocking = []
    if not validation["valid"]:
        blocking.append("POLICY_INVALID")
    if not policy.get("supervisor_enabled"):
        blocking.append("SUPERVISOR_DISABLED")
    if recovery.get("stop_requested"):
        blocking.append("STOP_FILE_REQUESTED")
    if not execute_child:
        blocking.append("CHILD_EXECUTION_NOT_AUTHORIZED")

    restarts = 0
    child_exit_code = None
    if not blocking:
        command = [
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", str(root / "RUN_V261_01_TO_V265_64_REAL_PAPER_SESSION.ps1"),
        ]
        while restarts <= int(policy["maximum_restarts"]):
            completed = subprocess.run(command, cwd=root)
            child_exit_code = completed.returncode
            if child_exit_code == 0 or not policy.get("restart_on_failure"):
                break
            restarts += 1
            if restarts > int(policy["maximum_restarts"]):
                break
            time.sleep(int(policy["restart_backoff_seconds"]))

    state = (
        "WINDOWS_AUTOSTART_RECOVERY_ACTIVE"
        if not blocking
        else "WINDOWS_AUTOSTART_RECOVERY_READY_BLOCKED"
    )
    result = {
        "stage": "V270.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "blocking_reasons": blocking,
        "stale_lock": stale,
        "recovery": recovery,
        "log_cleanup": log_cleanup,
        "restart_count": restarts,
        "child_exit_code": child_exit_code,
        "autostart_registration_enabled": policy.get("autostart_registration_enabled") is True,
        "supervisor_enabled": policy.get("supervisor_enabled") is True,
        "live_submission_enabled": False,
        "live_network_enabled": False,
        "broker_write_enabled": False,
        "actual_live_orders_submitted": 0,
        "next_phase": "V271_01_TO_V275_64_MULTI_TIMEFRAME_STRATEGY_ENGINE",
    }
    actual = root / "release/v266_01_to_v270_64/actual"
    write_json(actual / "windows_autostart_recovery_result.json", result)
    append_jsonl(actual / "windows_autostart_recovery_ledger.jsonl", {
        "observed_at": result["observed_at"],
        "state": state,
        "blocking_reasons": blocking,
        "restart_count": restarts,
        "actual_live_orders_submitted": 0,
    })
    return result
