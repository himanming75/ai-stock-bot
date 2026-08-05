from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_risk_governor.io import append_jsonl, read_json, write_json
from paper_portfolio.guard import run_fill_accounting

parser = argparse.ArgumentParser()
parser.add_argument(
    "--simulator-result",
    default="release/v392_11a/actual/paper_execution_simulator_result.json",
)
parser.add_argument(
    "--fill-event",
    default="release/v392_11a/actual/fill_event.json",
)
parser.add_argument(
    "--portfolio-state",
    default="release/v392_12a/actual/paper_portfolio_state.json",
)
parser.add_argument(
    "--registry",
    default="release/v392_12a/actual/applied_fill_registry.json",
)
parser.add_argument(
    "--output",
    default="release/v392_12a/actual/fill_accounting_position_update_result.json",
)
args = parser.parse_args()

simulator_result = read_json(ROOT / args.simulator_result)
fill_event = read_json(ROOT / args.fill_event)

portfolio_path = ROOT / args.portfolio_state
if portfolio_path.exists():
    portfolio_state = read_json(portfolio_path)
else:
    portfolio_state = {
        "portfolio_version": "V392.12A",
        "cash": 100000.0,
        "equity": 100000.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "positions": {},
    }

registry_path = ROOT / args.registry
if registry_path.exists():
    registry = read_json(registry_path)
else:
    registry = {"applied_fill_event_ids": []}

applied = set(registry.get("applied_fill_event_ids", []))

result = run_fill_accounting(
    simulator_result=simulator_result,
    fill_event=fill_event,
    portfolio_state=portfolio_state,
    applied_fill_event_ids=applied,
)

if result["portfolio_updated"]:
    applied.add(fill_event.get("fill_event_id"))
    write_json(
        portfolio_path,
        result["evaluation"]["portfolio_state"],
    )

write_json(
    registry_path,
    {"applied_fill_event_ids": sorted(applied)},
)
write_json(
    ROOT / "release/v392_12a/actual/fill_accounting_event.json",
    result["evaluation"].get("accounting_event", {}),
)
write_json(ROOT / args.output, result)
append_jsonl(
    ROOT / "release/v392_12a/actual/fill_accounting_ledger.jsonl",
    result,
)

print(json.dumps(result, indent=2, sort_keys=True))
