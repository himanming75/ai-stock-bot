from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from position_manager_v2.engine import evaluate
r = evaluate(ROOT)
s = r["snapshot"]
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "open_position_count": s["open_position_count"],
    "equity": r["exposure"]["equity"],
    "cash": r["exposure"]["cash"],
    "total_realized_pnl": s["total_realized_pnl"],
    "total_unrealized_pnl": s["total_unrealized_pnl"],
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
