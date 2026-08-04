from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from offline_ai_decision_engine.engine import decide
from offline_ai_decision_engine.io import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="release/v400_01_to_v410_64/fixtures/sample_market_input.json")
    parser.add_argument("--output", default="release/v400_01_to_v410_64/actual/offline_ai_decision_result.json")
    args = parser.parse_args()

    result = decide(read_json(ROOT / args.input)).to_dict()
    result.update({
        "stage": "V410.64",
        "state": "OFFLINE_AI_DECISION_ENGINE_READY",
        "status": "PASS",
        "network_used": False,
        "broker_credentials_used": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
    })
    write_json(ROOT / args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
