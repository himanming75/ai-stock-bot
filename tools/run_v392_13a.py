from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from paper_portfolio.reconciliation_guard import run_portfolio_reconciliation

parser = argparse.ArgumentParser()
parser.add_argument(
    "--accounting-result",
    default="release/v392_12a/actual/fill_accounting_position_update_result.json",
)
parser.add_argument(
    "--portfolio-state",
    default="release/v392_12a/actual/paper_portfolio_state.json",
)
parser.add_argument(
    "--accounting-event",
    default="release/v392_12a/actual/fill_accounting_event.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_12a/actual/applied_fill_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_13a/actual/paper_portfolio_reconciliation_result.json",
)
args = parser.parse_args()

accounting_result = read_json(ROOT / args.accounting_result)
portfolio_state = read_json(ROOT / args.portfolio_state)
accounting_event = read_json(ROOT / args.accounting_event)
registry = read_json(ROOT / args.registry)

result = run_portfolio_reconciliation(
    accounting_result=accounting_result,
    portfolio_state=portfolio_state,
    accounting_event=accounting_event,
    applied_fill_registry=registry,
)

write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_13a/actual/paper_portfolio_reconciliation_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
