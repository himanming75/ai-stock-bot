from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paper_operations_v2.engine import evaluate
r = evaluate(ROOT)
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "cycle_id": r["cycle_id"],
    "automatic_cycle_foundation_ready": r["automatic_cycle_foundation_ready"],
    "paper_submission_enabled": r["paper_submission_enabled"],
    "real_network_enabled": r["real_network_enabled"],
    "paper_orders_submitted": r["paper_orders_submitted"],
    "reconciliation_passed": r["reconciliation"]["passed"],
    "broker_write_enabled": r["broker_write_enabled"],
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
