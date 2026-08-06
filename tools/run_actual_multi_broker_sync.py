from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_sync.sync_engine import BrokerSyncEngine


parser = argparse.ArgumentParser()
parser.add_argument(
    "--alpaca",
    default=(
        "release/v8201_8400_broker_abstraction/"
        "actual/broker_unified_snapshot_fixture.json"
    ),
)
parser.add_argument(
    "--etrade",
    default=(
        "release/etrade_sandbox_live_read/actual/"
        "etrade_sandbox_read_only_validation.json"
    ),
)
parser.add_argument(
    "--output-dir",
    default=(
        "release/actual_multi_broker_sync/actual"
    ),
)
parser.add_argument(
    "--stale-after-seconds",
    type=float,
    default=900,
)
args = parser.parse_args()

result = BrokerSyncEngine().run(
    alpaca_path=Path(args.alpaca),
    etrade_path=Path(args.etrade),
    output_dir=Path(args.output_dir),
    stale_after_seconds=args.stale_after_seconds,
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(
    0 if result["status"] == "PASS" else 2
)
