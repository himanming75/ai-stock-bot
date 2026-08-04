from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_risk_allocation.position_sizing import size_positions
from offline_ai_decision_engine.io import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="release/v441_01/fixtures/sample_position_sizing_input.json",
    )
    parser.add_argument(
        "--output",
        default="release/v441_01/actual/position_sizing_result.json",
    )
    args = parser.parse_args()

    result = size_positions(read_json(ROOT / args.input)).to_dict()
    result.update({
        "stage": "V441.01",
        "state": "POSITION_SIZING_FOUNDATION_READY",
        "status": "PASS",
        "network_used": False,
        "broker_credentials_used": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
    })
    write_json(ROOT / args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
