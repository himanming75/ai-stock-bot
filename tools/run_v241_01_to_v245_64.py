from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from exit_manager_v2.engine import evaluate
r = evaluate(ROOT)
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "positions_evaluated": r["snapshot"]["positions_evaluated"],
    "exit_candidate_count": r["snapshot"]["exit_candidate_count"],
    "exit_reasons": [
        row["selected_exit"].get("reason")
        for row in r["snapshot"]["rows"]
        if row["exit_triggered"]
    ],
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
