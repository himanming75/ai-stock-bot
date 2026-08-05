from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from paper_dispatch_engine.guard import run_local_paper_dispatch_guard

parser = argparse.ArgumentParser()
parser.add_argument(
    "--preparation-result",
    default="release/v392_09a/actual/local_dispatch_engine_preparation_result.json",
)
parser.add_argument(
    "--dispatch-context",
    default="release/v392_09a/actual/dispatch_context.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_10a/actual/dispatched_context_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_10a/actual/local_paper_dispatch_engine_result.json",
)
args = parser.parse_args()

preparation_result = read_json(ROOT / args.preparation_result)
dispatch_context = read_json(ROOT / args.dispatch_context)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"dispatched_context_ids": []}

dispatched = set(registry.get("dispatched_context_ids", []))

result = run_local_paper_dispatch_guard(
    preparation_result=preparation_result,
    dispatch_context=dispatch_context,
    dispatched_context_ids=dispatched,
)

if result["local_dispatch_accepted"]:
    dispatched.add(dispatch_context.get("context_id"))

write_json(
    registry_path,
    {"dispatched_context_ids": sorted(dispatched)},
)
write_json(
    ROOT / "release/v392_10a/actual/local_paper_order.json",
    result["evaluation"].get("local_order", {}),
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_10a/actual/local_paper_dispatch_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
