from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from autonomous_paper_session.io import write_json

def save(root: Path, value: dict) -> dict:
    output = {
        **value,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "actual_live_orders_submitted": 0,
    }
    write_json(
        root / "release/v261_01_to_v265_64/actual/session_checkpoint.json",
        output,
    )
    return output
