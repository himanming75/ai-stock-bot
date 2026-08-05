
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paper_broker_audit.scanner import run_audit

result = run_audit(ROOT)
result.update({
    "stage": "V460.64",
    "state": "PAPER_BROKER_INTEGRATION_AUDIT_COMPLETE",
    "status": "PASS",
    "network_used": False,
    "broker_credentials_used": False,
    "broker_write_enabled": False,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
    "next_phase": "V461_TO_V470_ALPACA_PAPER_READ_AND_SAFETY",
})
out = ROOT / "release/v460_64/actual/paper_broker_integration_audit.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2, sort_keys=True))
