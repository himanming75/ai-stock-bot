from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from execution_authorization.local_dispatch_release_guard import (
    run_local_dispatch_release_gate,
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--release-token-result",
    default="release/v392_07a/actual/release_token_gate_result.json",
)
parser.add_argument(
    "--queue-state",
    default="release/v392_04a/actual/dispatch_queue_state.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_08a/actual/released_dispatch_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_08a/actual/local_dispatch_release_gate_result.json",
)
args = parser.parse_args()

release_token_result = read_json(ROOT / args.release_token_result)
queue_state = read_json(ROOT / args.queue_state)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"released_dispatch_ids": []}

released = set(registry.get("released_dispatch_ids", []))

result = run_local_dispatch_release_gate(
    release_token_result=release_token_result,
    queue_state=queue_state,
    released_dispatch_ids=released,
)

if result["local_dispatch_release_approved"]:
    released.add(result["evaluation"]["release_record"]["dispatch_id"])

write_json(
    registry_path,
    {"released_dispatch_ids": sorted(released)},
)
write_json(
    ROOT / "release/v392_08a/actual/local_dispatch_release_record.json",
    result["evaluation"]["release_record"],
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_08a/actual/local_dispatch_release_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
