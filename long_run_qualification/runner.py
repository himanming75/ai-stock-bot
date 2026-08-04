from __future__ import annotations
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from long_run_qualification.config import load, validate
from long_run_qualification.io import append_jsonl, write_json
from long_run_qualification.qualifier import qualify

ACTUAL = Path("release/v321_01_to_v330_64/actual")


def run(
    root: Path,
    allow_network: bool = False,
    sleep_enabled: bool = True,
    collector: Callable | None = None,
) -> dict:
    policy = load(root)
    validation = validate(policy)
    if collector is None:
        from real_paper_data_collection.collector import collect as collector

    started_wall = datetime.now(timezone.utc)
    started_mono = time.monotonic()
    cycles = successful = errors = consecutive_errors = 0
    market_was_open = False
    stop_reason = "MAXIMUM_CYCLES_REACHED"

    if not validation["valid"]:
        stop_reason = "POLICY_INVALID"
    elif not policy.get("qualification_enabled"):
        stop_reason = "QUALIFICATION_DISABLED"
    elif not allow_network:
        stop_reason = "NETWORK_NOT_AUTHORIZED"
    else:
        try:
            while cycles < int(policy["maximum_cycles_per_run"]):
                elapsed_minutes = (time.monotonic() - started_mono) / 60
                if elapsed_minutes >= float(policy["maximum_runtime_minutes"]):
                    stop_reason = "MAXIMUM_RUNTIME_REACHED"
                    break
                cycles += 1
                cycle_started = time.monotonic()
                try:
                    result = collector(root, allow_network=True)
                    active = result.get("state") == "REAL_PAPER_DATA_COLLECTION_ACTIVE"
                    blocking = bool(result.get("blocking_reasons"))
                    market_open = result.get("snapshot", {}).get("market_open") is True
                    market_was_open = market_was_open or market_open
                    if active:
                        successful += 1
                        consecutive_errors = 0
                    append_jsonl(root / ACTUAL / "long_run_cycle_ledger.jsonl", {
                        "observed_at": result.get("snapshot", {}).get("observed_at", datetime.now(timezone.utc).isoformat()),
                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                        "cycle": cycles,
                        "cycle_success": active,
                        "blocked": blocking,
                        "market_open": market_open,
                        "collector_state": result.get("state"),
                        "collector_status": result.get("status"),
                        "equity": result.get("metrics", {}).get("equity"),
                        "daily_pnl": result.get("metrics", {}).get("daily_pnl"),
                        "position_count": result.get("metrics", {}).get("position_count"),
                        "order_count": result.get("metrics", {}).get("order_count"),
                        "cycle_runtime_seconds": round(time.monotonic() - cycle_started, 3),
                        "actual_paper_orders_submitted": 0,
                        "actual_live_orders_submitted": 0,
                    })
                    write_json(root / ACTUAL / "long_run_checkpoint.json", {
                        "stage": "V330.64", "last_completed_cycle": cycles,
                        "successful_cycles": successful, "errors": errors,
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "actual_paper_orders_submitted": 0,
                        "actual_live_orders_submitted": 0,
                    })
                    if blocking:
                        stop_reason = "COLLECTOR_BLOCKED"
                        break
                    if market_was_open and not market_open and policy.get("stop_after_market_close"):
                        stop_reason = "MARKET_CLOSED_AFTER_OPEN"
                        break
                except Exception as error:
                    errors += 1
                    consecutive_errors += 1
                    append_jsonl(root / ACTUAL / "long_run_error_ledger.jsonl", {
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "cycle": cycles,
                        "error_type": type(error).__name__,
                        "error": str(error),
                        "consecutive_errors": consecutive_errors,
                    })
                    if consecutive_errors > int(policy.get("maximum_consecutive_errors", 3)):
                        stop_reason = "CONSECUTIVE_ERROR_LIMIT"
                        break

                if sleep_enabled and cycles < int(policy["maximum_cycles_per_run"]):
                    base = int(policy["cycle_interval_seconds"])
                    if consecutive_errors:
                        base = min(
                            int(policy.get("maximum_retry_delay_seconds", 120)),
                            int(policy.get("retry_delay_seconds", 10)) * (2 ** (consecutive_errors - 1)),
                        )
                    time.sleep(base)
        except KeyboardInterrupt:
            stop_reason = "USER_INTERRUPTED_SAFE"

    qualification = qualify(root)
    summary = {
        "stage": "V330.64",
        "state": "REAL_PAPER_LONG_RUN_SESSION_COMPLETE" if stop_reason != "USER_INTERRUPTED_SAFE" else "REAL_PAPER_LONG_RUN_SESSION_INTERRUPTED_SAFE",
        "status": "PASS",
        "started_at": started_wall.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "cycles": cycles,
        "successful_cycles": successful,
        "errors": errors,
        "market_was_open": market_was_open,
        "stop_reason": stop_reason,
        "qualification_state": qualification["state"],
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    write_json(root / ACTUAL / "real_paper_long_run_session_summary.json", summary)
    return summary
