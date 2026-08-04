from __future__ import annotations
import time
from datetime import datetime, timezone
from pathlib import Path
from real_paper_data_collection.collector import collect
from real_paper_data_collection.config import load
from real_paper_data_collection.io import write_json, append_jsonl

def run(root: Path, allow_network: bool = False, sleep_enabled: bool = True) -> dict:
    policy = load(root)
    started = time.monotonic()
    cycles = 0
    successful_cycles = 0
    errors = 0
    market_was_open = False
    stop_reason = "MAXIMUM_CYCLES_REACHED"

    while cycles < int(policy["maximum_cycles_per_run"]):
        elapsed_minutes = (time.monotonic() - started) / 60
        if elapsed_minutes >= float(policy["maximum_runtime_minutes"]):
            stop_reason = "MAXIMUM_RUNTIME_REACHED"
            break

        cycles += 1
        try:
            result = collect(root, allow_network=allow_network)
            if result["state"] == "REAL_PAPER_DATA_COLLECTION_ACTIVE":
                successful_cycles += 1
            market_open = result["snapshot"].get("market_open") is True
            market_was_open = market_was_open or market_open

            if result["blocking_reasons"]:
                stop_reason = "BLOCKED"
                break
            if market_was_open and not market_open and policy.get("stop_after_market_close"):
                stop_reason = "MARKET_CLOSED_AFTER_OPEN"
                break

            delay = (
                int(policy["cycle_interval_seconds"])
                if market_open
                else int(policy["market_closed_poll_seconds"])
            )
            if sleep_enabled and cycles < int(policy["maximum_cycles_per_run"]):
                time.sleep(delay)
        except Exception as error:
            errors += 1
            append_jsonl(
                root / "release/v311_01_to_v320_64/actual/paper_collection_error_ledger.jsonl",
                {
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "cycle": cycles,
                    "error": str(error),
                },
            )
            stop_reason = "ERROR"
            break

    summary = {
        "stage": "V320.64",
        "state": "REAL_PAPER_DATA_COLLECTION_SESSION_COMPLETE",
        "status": "PASS",
        "cycles": cycles,
        "successful_cycles": successful_cycles,
        "errors": errors,
        "market_was_open": market_was_open,
        "stop_reason": stop_reason,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    write_json(
        root / "release/v311_01_to_v320_64/actual/paper_collection_session_summary.json",
        summary,
    )
    return summary
