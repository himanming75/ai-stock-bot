from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from live_shadow_slippage.engine import evaluate
r = evaluate(ROOT)
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "symbol": r["signal"].get("symbol"),
    "paper_price": r["slippage"]["paper_reference_price"],
    "expected_live_fill": r["slippage"]["expected_live_fill_price"],
    "spread_pct": r["quote"]["spread_pct"],
    "slippage_pct": r["slippage"]["slippage_pct"],
    "qualification_score": r["qualification"]["score"],
    "shadow_qualified": r["qualification"]["passed"],
    "real_live_read_enabled": r["real_live_read_enabled"],
    "broker_write_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
