from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_paper_read.adapter import AlpacaPaperReadAdapter
from alpaca_paper_read.config import load_config
from alpaca_paper_read.fixture_adapter import FixtureReadAdapter
from alpaca_paper_read.http_client import ReadOnlyHttpClient
from alpaca_paper_read.io import append_jsonl, read_json, write_json
from alpaca_paper_read.service import run_read_snapshot


parser = argparse.ArgumentParser()
parser.add_argument(
    "--fixture",
    default="release/v470_64/fixtures/alpaca_paper_read_fixture.json",
)
parser.add_argument(
    "--symbols",
    default="AAPL,MSFT,SPY",
)
parser.add_argument(
    "--actual-read",
    action="store_true",
)
args = parser.parse_args()

symbols = [value.strip() for value in args.symbols.split(",") if value.strip()]

if args.actual_read:
    config = load_config()
    if not config.actual_network_enabled:
        raise SystemExit(
            "Set ALPACA_PAPER_READ_ENABLE=true before --actual-read."
        )
    adapter = AlpacaPaperReadAdapter(ReadOnlyHttpClient(config))
    mode = "ACTUAL_ALPACA_PAPER_READ_ONLY"
else:
    fixture = read_json(ROOT / args.fixture)
    adapter = FixtureReadAdapter(fixture)
    mode = "OFFLINE_FIXTURE_READ_ONLY"

result = run_read_snapshot(adapter, symbols, mode)

output = (
    ROOT
    / "release/v470_64/actual/alpaca_paper_read_safety_result.json"
)
write_json(output, result)
write_json(
    ROOT / "release/v470_64/actual/alpaca_paper_snapshot.json",
    result["snapshot"],
)
append_jsonl(
    ROOT / "release/v470_64/actual/alpaca_paper_read_audit_ledger.jsonl",
    result,
)

summary = {
    "stage": result["stage"],
    "state": result["state"],
    "status": result["status"],
    "mode": result["mode"],
    "snapshot_hash": result["integrity"]["snapshot_hash"],
    "account_status": result["snapshot"]["account"]["status"],
    "equity": result["snapshot"]["account"]["equity"],
    "buying_power": result["snapshot"]["account"]["buying_power"],
    "position_count": len(result["snapshot"]["positions"]),
    "open_order_count": len(result["snapshot"]["open_orders"]),
    "market_open": result["snapshot"]["clock"]["is_open"],
    "asset_symbols": sorted(result["snapshot"]["assets"]),
    "broker_write_enabled": False,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(summary, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
