from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adaptive_rebalance.engine import evaluate

def main() -> int:
    result = evaluate(ROOT)
    summary = {
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "adaptive_rebalance_id": result.get("adaptive_rebalance_id"),
        "primary_regime": result.get("regime", {}).get("primary_regime"),
        "volatility_regime": result.get("regime", {}).get("volatility_regime"),
        "regime_multiplier": result.get("regime_multiplier"),
        "actionable_adjustment_count": result.get("actionable_adjustment_count", 0),
        "stability_score": result.get("stability", {}).get("stability_score"),
        "stability_level": result.get("stability", {}).get("stability_level"),
        "gate_passed": result.get("optimization_gate", {}).get("passed"),
        "manual_approval_required": result.get("manual_approval_required"),
        "execution_authorized": result.get("execution_authorized"),
        "actual_orders_submitted": result.get("actual_orders_submitted"),
        "paper_only": result.get("paper_only"),
        "next_phase": result.get("next_phase"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT / "release/v101_33_to_v101_64/actual/"
                "adaptive_rebalance_optimization_result.json"
            ).resolve()
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
