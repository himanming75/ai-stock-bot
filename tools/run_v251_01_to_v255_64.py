from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from execution_optimizer.engine import evaluate
r = evaluate(ROOT)
p = r["execution_plan"]
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "symbol": p.get("symbol"),
    "action": p.get("action"),
    "order_type": p.get("order_type"),
    "limit_price": p.get("limit_price"),
    "time_in_force": p.get("time_in_force"),
    "fill_probability_pct": r["fill_probability"]["fill_probability_pct"],
    "expected_slippage_pct": r["slippage"]["expected_slippage_pct"],
    "execution_authorized": False,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
