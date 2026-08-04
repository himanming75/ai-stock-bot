from __future__ import annotations
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from autonomous_paper_session.checkpoint import save
from autonomous_paper_session.config import load, validate
from autonomous_paper_session.io import write_json, append_jsonl
from autonomous_paper_session.lock import SessionLock
from autonomous_paper_session.stop import requested

CycleFunction = Callable[[Path, bool], dict]

def run(
    root: Path,
    cycle_function: CycleFunction,
    allow_network: bool = False,
    sleep_enabled: bool = True,
) -> dict:
    policy = load(root)
    validation = validate(policy)
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    started = time.monotonic()

    blocking = []
    if not validation["valid"]:
        blocking.append("POLICY_INVALID")
    if not policy.get("session_runner_enabled"):
        blocking.append("SESSION_RUNNER_DISABLED")
    if allow_network and not policy.get("allow_real_paper_network"):
        blocking.append("REAL_PAPER_NETWORK_POLICY_DISABLED")
    if not allow_network:
        blocking.append("NETWORK_NOT_AUTHORIZED_FOR_SESSION")

    if blocking:
        result = {
            "stage": "V265.64",
            "state": "AUTONOMOUS_PAPER_SESSION_READY_BLOCKED",
            "status": "PASS",
            "session_id": session_id,
            "cycle_count": 0,
            "paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "blocking_reasons": blocking,
            "stop_reason": "BLOCKED_BEFORE_START",
            "next_phase": "V266_01_TO_V270_64_WINDOWS_AUTOSTART_AND_RECOVERY",
        }
        save(root, result)
        write_json(root / "release/v261_01_to_v265_64/actual/session_runner_result.json", result)
        return result

    lock_path = root / "release/v261_01_to_v265_64/control/session_runner.lock"
    cycles = 0
    paper_orders = 0
    consecutive_errors = 0
    market_was_open = False
    stop_reason = "MAXIMUM_CYCLES_REACHED"

    with SessionLock(lock_path):
        while cycles < int(policy["maximum_cycles_per_session"]):
            elapsed_minutes = (time.monotonic() - started) / 60
            if elapsed_minutes >= float(policy["maximum_runtime_minutes"]):
                stop_reason = "MAXIMUM_RUNTIME_REACHED"
                break
            if requested(root):
                stop_reason = "STOP_FILE_REQUESTED"
                break

            try:
                cycle = cycle_function(root, allow_network)
                cycles += 1
                paper_orders += int(cycle.get("actual_paper_orders_submitted", 0) or 0)
                market_open = cycle.get("market_open") is True
                market_was_open = market_was_open or market_open
                consecutive_errors = 0

                append_jsonl(
                    root / "release/v261_01_to_v265_64/actual/session_cycle_ledger.jsonl",
                    {
                        "session_id": session_id,
                        "cycle_number": cycles,
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "market_open": market_open,
                        "cycle_state": cycle.get("state"),
                        "paper_orders_submitted": cycle.get("actual_paper_orders_submitted", 0),
                        "actual_live_orders_submitted": 0,
                    },
                )
                save(root, {
                    "stage": "V265.64",
                    "session_id": session_id,
                    "cycle_count": cycles,
                    "paper_orders_submitted": paper_orders,
                    "market_open": market_open,
                    "last_cycle_state": cycle.get("state"),
                    "runner_state": "RUNNING",
                })

                if market_was_open and not market_open and policy.get("stop_after_market_close"):
                    stop_reason = "MARKET_CLOSED_AFTER_OPEN"
                    break

                delay = (
                    int(policy["cycle_interval_seconds"])
                    if market_open
                    else int(policy["market_closed_poll_seconds"])
                )
                if sleep_enabled and cycles < int(policy["maximum_cycles_per_session"]):
                    time.sleep(delay)
            except Exception as error:
                consecutive_errors += 1
                append_jsonl(
                    root / "release/v261_01_to_v265_64/actual/session_error_ledger.jsonl",
                    {
                        "session_id": session_id,
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "error": str(error),
                        "consecutive_errors": consecutive_errors,
                        "actual_live_orders_submitted": 0,
                    },
                )
                if consecutive_errors >= int(policy["maximum_consecutive_errors"]):
                    stop_reason = "MAXIMUM_CONSECUTIVE_ERRORS"
                    break
                if sleep_enabled:
                    time.sleep(int(policy["error_backoff_seconds"]))

    result = {
        "stage": "V265.64",
        "state": "AUTONOMOUS_PAPER_SESSION_COMPLETE",
        "status": "PASS",
        "session_id": session_id,
        "cycle_count": cycles,
        "paper_orders_submitted": paper_orders,
        "actual_live_orders_submitted": 0,
        "market_was_open": market_was_open,
        "blocking_reasons": [],
        "stop_reason": stop_reason,
        "next_phase": "V266_01_TO_V270_64_WINDOWS_AUTOSTART_AND_RECOVERY",
    }
    save(root, result)
    write_json(root / "release/v261_01_to_v265_64/actual/session_runner_result.json", result)
    return result
