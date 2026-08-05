from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from execution_authorization.dispatch_context_guard import (
    run_dispatch_engine_preparation,
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--release-gate-result",
    default="release/v392_08a/actual/local_dispatch_release_gate_approved_snapshot.json",
)
parser.add_argument(
    "--preparation-result",
    default="release/v392_03a/actual/dispatch_preparation_result.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_09a/actual/dispatch_context_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_09a/actual/local_dispatch_engine_preparation_result.json",
)
args = parser.parse_args()

release_gate_result = read_json(ROOT / args.release_gate_result)
preparation_result = read_json(ROOT / args.preparation_result)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"context_ids": []}

existing = set(registry.get("context_ids", []))

result = run_dispatch_engine_preparation(
    release_gate_result=release_gate_result,
    preparation_result=preparation_result,
    existing_context_ids=existing,
)

if result["dispatch_context_created"]:
    existing.add(result["evaluation"]["context_id"])

write_json(
    registry_path,
    {"context_ids": sorted(existing)},
)
write_json(
    ROOT / "release/v392_09a/actual/dispatch_context.json",
    result["evaluation"]["dispatch_context"],
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_09a/actual/dispatch_context_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
