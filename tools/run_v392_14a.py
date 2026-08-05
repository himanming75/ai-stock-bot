from __future__ import annotations
import argparse
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from autonomous_paper_cycle.guard import run_autonomous_paper_cycle

parser = argparse.ArgumentParser()
parser.add_argument(
    "--risk-result",
    default="release/v391_06a/actual/symbol_concentration_guard_result.json",
)
parser.add_argument(
    "--authorization-result",
    default="release/v392_09a/actual/local_dispatch_engine_preparation_result.json",
)
parser.add_argument(
    "--dispatch-result",
    default="release/v392_10a/actual/local_paper_dispatch_engine_result.json",
)
parser.add_argument(
    "--simulator-result",
    default="release/v392_11a/actual/paper_execution_simulator_approved_snapshot.json",
)
parser.add_argument(
    "--accounting-result",
    default="release/v392_12a/actual/fill_accounting_position_update_result.json",
)
parser.add_argument(
    "--reconciliation-result",
    default="release/v392_13a/actual/paper_portfolio_reconciliation_result.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_14a/actual/completed_cycle_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_14a/actual/autonomous_paper_cycle_result.json",
)
args = parser.parse_args()

risk_result = read_json(ROOT / args.risk_result)
authorization_result = read_json(ROOT / args.authorization_result)
dispatch_result = read_json(ROOT / args.dispatch_result)
simulator_result = read_json(ROOT / args.simulator_result)
accounting_result = read_json(ROOT / args.accounting_result)
reconciliation_result = read_json(ROOT / args.reconciliation_result)

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"completed_cycle_ids": []}

completed = set(registry.get("completed_cycle_ids", []))
cycle_id = f"cycle-{secrets.token_hex(12)}"

result = run_autonomous_paper_cycle(
    risk_result=risk_result,
    authorization_result=authorization_result,
    dispatch_result=dispatch_result,
    simulator_result=simulator_result,
    accounting_result=accounting_result,
    reconciliation_result=reconciliation_result,
    cycle_id=cycle_id,
    completed_cycle_ids=completed,
)

if result["cycle_completed"]:
    completed.add(cycle_id)

write_json(
    registry_path,
    {"completed_cycle_ids": sorted(completed)},
)
write_json(
    ROOT / "release/v392_14a/actual/autonomous_paper_cycle_report.json",
    result["evaluation"]["cycle_report"],
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_14a/actual/autonomous_paper_cycle_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
