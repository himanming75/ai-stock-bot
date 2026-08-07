from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

path = Path("runtime/paper_autonomous_execution/arm_token.json")
path.parent.mkdir(parents=True, exist_ok=True)
data = {
    "mode": "PAPER_ONLY",
    "armed": True,
    "live_submission_enabled": False,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
}
path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
    encoding="utf-8",
)
print("PAPER ARM TOKEN: CREATED")
print("LIVE SUBMISSION: OFF")
