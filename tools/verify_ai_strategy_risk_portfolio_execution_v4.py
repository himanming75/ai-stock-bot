from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "release/ai_strategy_risk_portfolio_execution_v4/actual/ai_strategy_risk_portfolio_execution_result.json"
r = json.loads(p.read_text(encoding="utf-8-sig"))
checks = {
    "status": r.get("status") == "PASS",
    "network_unused": r.get("actual_external_network_used") is False,
    "broker_write_unused": r.get("actual_broker_write_performed") is False,
    "orders_zero": r.get("actual_paper_orders_submitted") == 0 and r.get("actual_live_orders_submitted") == 0,
}
v = {"verification_stage":"AI_STRATEGY_RISK_PORTFOLIO_EXECUTION_V4","verification_status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"failed":[k for k,v in checks.items() if not v]}
print(json.dumps(v, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
