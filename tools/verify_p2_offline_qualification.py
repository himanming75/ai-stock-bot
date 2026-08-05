from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
value = json.loads(
    (
        ROOT
        / "release/p2_actual_paper_execution/actual/"
          "p2_offline_qualification.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": value.get("stage") == "P2",
    "status": value.get("status") == "PASS",
    "state": (
        value.get("state")
        == "ACTUAL_ALPACA_PAPER_EXECUTION_OFFLINE_QUALIFIED"
    ),
    "market": value.get("market_order_supported") is True,
    "limit": value.get("limit_order_supported") is True,
    "buy_sell": value.get("buy_sell_supported") is True,
    "fractional": value.get("fractional_market_supported") is True,
    "notional": value.get("notional_market_supported") is True,
    "idempotency": value.get("idempotency_enabled") is True,
    "cancel": value.get("cancel_supported") is True,
    "replace": value.get("replace_supported") is True,
    "kill_switch": value.get("kill_switch_required") is True,
    "paper_endpoint": value.get("paper_endpoint_enforced") is True,
    "network_unused": value.get("actual_network_used") is False,
    "paper_orders_zero": value.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": value.get("actual_live_orders_submitted") == 0,
}
result = {
    "verification_stage": "P2_OFFLINE_QUALIFICATION",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
