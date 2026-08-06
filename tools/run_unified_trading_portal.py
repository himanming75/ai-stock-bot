from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from unified_trading_portal.web import serve


parser = argparse.ArgumentParser()
parser.add_argument(
    "--host",
    default="127.0.0.1",
)
parser.add_argument(
    "--port",
    type=int,
    default=8768,
)
parser.add_argument(
    "--portal-path",
    default=(
        "release/actual_multi_broker_sync/actual/"
        "multi_broker_portal_snapshot.json"
    ),
)
parser.add_argument(
    "--sync-result-path",
    default=(
        "release/actual_multi_broker_sync/actual/"
        "broker_sync_result.json"
    ),
)
args = parser.parse_args()

serve(
    portal_path=Path(args.portal_path),
    sync_result_path=Path(
        args.sync_result_path
    ),
    host=args.host,
    port=args.port,
)
