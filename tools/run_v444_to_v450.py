
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai_risk_allocation.allocation_qualification import qualify_allocation
def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="release/v450_64/fixtures/sample_integrated_allocation_input.json")
    p.add_argument("--output", default="release/v450_64/actual/integrated_allocation_qualification_result.json")
    a = p.parse_args()
    result = qualify_allocation(read_json(ROOT / a.input))
    result.update({
        "stage": "V450.64",
        "state": "AI_RISK_ALLOCATION_QUALIFIED" if result["qualified"] else "AI_RISK_ALLOCATION_BLOCKED",
        "status": "PASS" if result["qualified"] else "FAIL",
        "network_used": False,
        "broker_credentials_used": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "order_submission_allowed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "PAPER_BROKER_INTEGRATION_AUDIT",
    })
    write_json(ROOT / a.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["qualified"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
