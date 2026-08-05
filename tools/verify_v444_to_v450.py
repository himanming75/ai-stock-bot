
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "release/v450_64/actual/integrated_allocation_qualification_result.json"
r = json.loads(p.read_text(encoding="utf-8-sig"))
checks = {
    "stage": r.get("stage") == "V450.64",
    "status": r.get("status") == "PASS",
    "qualified": r.get("qualified") is True,
    "allocation_hash": len(str(r.get("allocation_hash",""))) == 64,
    "sector_exposure": isinstance(r.get("sector_exposure"), dict),
    "risk_budget": r.get("remaining_risk_budget") is not None,
    "drawdown_scaling": r.get("drawdown_multiplier") is not None,
    "correlation": r.get("correlation_threshold") is not None,
    "cash_reserve": r.get("required_cash_reserve_amount") is not None,
    "network_off": r.get("network_used") is False,
    "broker_credentials_off": r.get("broker_credentials_used") is False,
    "paper_submission_off": r.get("paper_submission_enabled") is False,
    "live_submission_off": r.get("live_submission_enabled") is False,
    "broker_write_off": r.get("broker_write_enabled") is False,
    "paper_orders_zero": r.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": r.get("actual_live_orders_submitted") == 0,
}
out = {"verification_stage":"V450.64","verification_status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"failed":[k for k,v in checks.items() if not v]}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
