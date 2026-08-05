from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from paper_dispatch_engine.simulator_guard import run_paper_execution_simulator

parser = argparse.ArgumentParser()
parser.add_argument(
    "--dispatch-result",
    default="release/v392_10a/actual/local_paper_dispatch_engine_result.json",
)
parser.add_argument(
    "--local-order",
    default="release/v392_10a/actual/local_paper_order.json",
)
parser.add_argument(
    "--market-snapshot",
    default="release/v392_11a/fixtures/sample_market_snapshot.json",
)
parser.add_argument(
    "--policy",
    default="release/v392_11a/config/paper_execution_simulator_policy.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_11a/actual/simulated_execution_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_11a/actual/paper_execution_simulator_result.json",
)
args = parser.parse_args()

dispatch_result = read_json(ROOT / args.dispatch_result)
local_order = read_json(ROOT / args.local_order)
market_snapshot = read_json(ROOT / args.market_snapshot)
policy = read_json(ROOT / args.policy)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"simulated_execution_ids": []}

simulated = set(registry.get("simulated_execution_ids", []))

result = run_paper_execution_simulator(
    dispatch_result=dispatch_result,
    local_order=local_order,
    market_snapshot=market_snapshot,
    policy=policy,
    simulated_execution_ids=simulated,
)

if result["simulated_fill_created"]:
    simulated.add(local_order.get("local_execution_id"))

write_json(
    registry_path,
    {"simulated_execution_ids": sorted(simulated)},
)
write_json(
    ROOT / "release/v392_11a/actual/fill_event.json",
    result["evaluation"].get("fill_event", {}),
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_11a/actual/paper_execution_simulator_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
