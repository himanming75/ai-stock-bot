from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from order_lifecycle_v2.engine import evaluate
r = evaluate(ROOT)
o = r["order"]
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "client_order_id": o["client_order_id"],
    "broker_order_id": o["broker_order_id"],
    "order_state": o["state"],
    "ordered_quantity": o["quantity"],
    "filled_quantity": o["filled_quantity"],
    "remaining_quantity": o["remaining_quantity"],
    "average_fill_price": o["average_fill_price"],
    "duplicate": r["duplicate"]["duplicate"],
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
