from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from execution_authorization.dispatch_queue_guard import run_dispatch_queue_gate

parser = argparse.ArgumentParser()
parser.add_argument(
    "--preparation-result",
    default="release/v392_03a/actual/dispatch_preparation_result.json",
)
parser.add_argument(
    "--queue-state",
    default="release/v392_04a/actual/dispatch_queue_state.json",
)
parser.add_argument(
    "--owner",
    default="local-dispatch-queue-manager",
)
parser.add_argument(
    "--output",
    default="release/v392_04a/actual/dispatch_queue_gate_result.json",
)
args = parser.parse_args()

queue_path = ROOT / args.queue_state
if queue_path.exists():
    queue_state = read_json(queue_path)
else:
    queue_state = {
        "queue_version": "V392.04A",
        "entries": [],
        "lock": {
            "locked": False,
            "owner": "",
            "locked_at": None,
        },
    }

preparation_result = read_json(ROOT / args.preparation_result)

result = run_dispatch_queue_gate(
    queue_state=queue_state,
    preparation_result=preparation_result,
    owner=args.owner,
)

if result["queue_entry_created"]:
    write_json(queue_path, result["evaluation"]["queue_state"])

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_04a/actual/dispatch_queue_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
