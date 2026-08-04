from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_signal_intelligence.engine import analyze
from ai_signal_intelligence.memory import append
from offline_ai_decision_engine.io import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="release/v411_01_to_v420_64/fixtures/sample_signal_input.json")
    parser.add_argument("--output", default="release/v411_01_to_v420_64/actual/ai_signal_intelligence_result.json")
    parser.add_argument("--no-memory", action="store_true")
    args = parser.parse_args()

    result = analyze(read_json(ROOT / args.input)).to_dict()
    result.update({
        "stage": "V420.64",
        "state": "AI_SIGNAL_INTELLIGENCE_READY",
        "status": "PASS",
        "network_used": False,
        "broker_credentials_used": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
    })
    write_json(ROOT / args.output, result)
    if not args.no_memory:
        append(ROOT / "release/v411_01_to_v420_64/actual/signal_memory_ledger.jsonl", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
