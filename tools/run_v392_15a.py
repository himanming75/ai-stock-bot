from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from autonomous_paper_cycle.qualification_guard import run_full_qualification

def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for raw in handle:
            line = raw.strip()
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records

parser = argparse.ArgumentParser()
parser.add_argument(
    "--cycle-result",
    default="release/v392_14a/actual/autonomous_paper_cycle_result.json",
)
parser.add_argument(
    "--cycle-report",
    default="release/v392_14a/actual/autonomous_paper_cycle_report.json",
)
parser.add_argument(
    "--cycle-ledger",
    default="release/v392_14a/actual/autonomous_paper_cycle_ledger.jsonl",
)
parser.add_argument(
    "--completed-cycle-registry",
    default="release/v392_14a/actual/completed_cycle_registry.json",
)
parser.add_argument(
    "--reconciliation-result",
    default="release/v392_13a/actual/paper_portfolio_reconciliation_result.json",
)
parser.add_argument(
    "--risk-result",
    default="release/v391_06a/actual/symbol_concentration_guard_result.json",
)
parser.add_argument(
    "--qualification-registry",
    default="release/v392_15a/actual/qualification_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_15a/actual/fully_autonomous_paper_qualification_result.json",
)
args = parser.parse_args()

cycle_result = read_json(ROOT / args.cycle_result)
cycle_report = read_json(ROOT / args.cycle_report)
cycle_ledger_records = read_jsonl(ROOT / args.cycle_ledger)
completed_cycle_registry = read_json(ROOT / args.completed_cycle_registry)
reconciliation_result = read_json(ROOT / args.reconciliation_result)
risk_result = read_json(ROOT / args.risk_result)

qualification_registry_path = ROOT / args.qualification_registry
if qualification_registry_path.exists():
    qualification_registry = read_json(qualification_registry_path)
else:
    qualification_registry = {"qualified_cycle_ids": []}

result = run_full_qualification(
    cycle_result=cycle_result,
    cycle_report=cycle_report,
    cycle_ledger_records=cycle_ledger_records,
    completed_cycle_registry=completed_cycle_registry,
    reconciliation_result=reconciliation_result,
    risk_result=risk_result,
    qualification_registry=qualification_registry,
)

if result["fully_autonomous_local_paper_trading_ready"]:
    ids = set(qualification_registry.get("qualified_cycle_ids", []))
    ids.add(cycle_report.get("cycle_id"))
    qualification_registry = {"qualified_cycle_ids": sorted(ids)}

write_json(qualification_registry_path, qualification_registry)
write_json(
    ROOT / "release/v392_15a/actual/qualification_certificate.json",
    result["evaluation"]["certificate"],
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_15a/actual/qualification_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
