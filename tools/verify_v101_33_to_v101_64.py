import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v101_33_to_v101_64/actual/"
    "adaptive_rebalance_optimization_result.json"
)
if not path.exists():
    raise SystemExit("RESULT NOT FOUND")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "stage": result.get("stage_range") == "V101.33-V101.64",
    "status": result.get("status") == "PASS",
    "allowed_state": result.get("state") in {
        "ADAPTIVE_REBALANCE_SOURCE_REQUIRED",
        "ADAPTIVE_REBALANCE_OPTIMIZATION_READY",
        "ADAPTIVE_REBALANCE_OPTIMIZATION_NO_ACTION",
        "ADAPTIVE_REBALANCE_OPTIMIZATION_REVIEW_REQUIRED",
    },
    "hash_valid": (
        len(result.get("adaptive_rebalance_certificate_sha256", "")) == 64
        if result.get("state") != "ADAPTIVE_REBALANCE_SOURCE_REQUIRED"
        else True
    ),
    "regime_valid": isinstance(result.get("regime", {}), dict),
    "adjustments_valid": isinstance(
        result.get("optimized_adjustments", []), list
    ),
    "stability_valid": isinstance(result.get("stability", {}), dict),
    "gate_valid": isinstance(result.get("optimization_gate", {}), dict),
    "execution_not_authorized": result.get("execution_authorized") is False,
    "manual_approval_required": result.get("manual_approval_required") is True,
    "credentials_unused": result.get("actual_credentials_used") is False,
    "network_unused": result.get("actual_external_network_used") is False,
    "orders_zero": result.get("actual_orders_submitted") == 0,
    "paper_only": result.get("paper_only") is True,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "orders_disabled": result.get("order_submission_enabled") is False,
    "live_disabled": result.get("live_trading_enabled") is False,
    "network_disabled": result.get("external_network_enabled") is False,
}
failed = [name for name, passed in checks.items() if not passed]

print(json.dumps({
    "verification_stage": "V101.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result.get("state"),
    "adaptive_rebalance_id": result.get("adaptive_rebalance_id"),
    "regime": result.get("regime"),
    "regime_multiplier": result.get("regime_multiplier"),
    "optimized_adjustments": result.get("optimized_adjustments"),
    "stability": result.get("stability"),
    "optimization_gate": result.get("optimization_gate"),
    "checks": checks,
    "failed": failed,
}, indent=2, sort_keys=True))

raise SystemExit(0 if not failed else 1)
