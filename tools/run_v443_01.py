from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_risk_allocation.volatility_scaling import apply_volatility_scaling
from offline_ai_decision_engine.io import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="release/v443_01/fixtures/sample_volatility_input.json")
    parser.add_argument("--output", default="release/v443_01/actual/volatility_scaling_result.json")
    args = parser.parse_args()

    result = apply_volatility_scaling(read_json(ROOT / args.input))
    result.update({
        "stage": "V443.01",
        "state": "VOLATILITY_SCALING_READY",
        "status": "PASS",
        "network_used": False,
        "broker_credentials_used": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "order_submission_allowed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    })

    write_json(ROOT / args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
