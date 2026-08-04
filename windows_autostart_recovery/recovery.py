from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from windows_autostart_recovery.io import load_json, write_json

def inspect(root: Path) -> dict:
    session = load_json(root / "release/v261_01_to_v265_64/actual/session_checkpoint.json")
    paper = load_json(root / "release/v256_01_to_v260_64/actual/autonomous_paper_trading_result.json")
    stop = load_json(root / "release/v261_01_to_v265_64/control/session_stop.json")
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_checkpoint_present": bool(session),
        "paper_checkpoint_present": bool(paper),
        "stop_requested": stop.get("stop_requested") is True,
        "last_session_id": session.get("session_id"),
        "last_cycle_count": session.get("cycle_count", 0),
        "last_runner_state": session.get("runner_state") or session.get("state"),
        "steps": [
            "READ_LAST_SESSION_CHECKPOINT",
            "READ_LAST_PAPER_CYCLE",
            "CHECK_STOP_FILE",
            "CHECK_STALE_LOCK",
            "READ_PAPER_ACCOUNT",
            "READ_OPEN_ORDERS",
            "READ_POSITIONS",
            "RECONCILE_BEFORE_RESUME",
            "RESUME_SESSION_RUNNER_ONLY_IF_SAFE",
        ],
        "automatic_live_resume_allowed": False,
        "actual_live_orders_submitted": 0,
    }
    write_json(root / "release/v266_01_to_v270_64/actual/recovery_plan.json", result)
    return result
