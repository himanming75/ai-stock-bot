from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from execution_authorization.queue_inspection_guard import run_queue_inspection_gate

parser = argparse.ArgumentParser()
parser.add_argument(
    "--queue-state",
    default="release/v392_04a/actual/dispatch_queue_state.json",
)
parser.add_argument(
    "--maximum-entry-age-seconds",
    type=int,
    default=900,
)
parser.add_argument(
    "--output",
    default="release/v392_05a/actual/queue_inspection_gate_result.json",
)
args = parser.parse_args()

queue_state = read_json(ROOT / args.queue_state)

result = run_queue_inspection_gate(
    queue_state=queue_state,
    maximum_entry_age_seconds=args.maximum_entry_age_seconds,
)

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_05a/actual/queue_inspection_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
