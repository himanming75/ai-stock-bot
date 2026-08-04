from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ai_strategy_ensemble_v3.engine import evaluate
r = evaluate(ROOT)
c = r["final_trade_candidate"]
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "market_regime": r["market_regime"]["regime"],
    "active_strategy_count": len(r["allocations"]),
    "candidate_symbol": c.get("symbol"),
    "candidate_action": c.get("action"),
    "candidate_confidence": c.get("confidence"),
    "gate_passed": c.get("gate_passed"),
    "execution_authorized": False,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
