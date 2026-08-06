from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_configuration.web import serve


parser = argparse.ArgumentParser()
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8770)
args = parser.parse_args()

serve(
    draft_path=Path(
        "release/trading_configuration/actual/"
        "configuration_draft.json"
    ),
    ledger_path=Path(
        "release/trading_configuration/actual/"
        "configuration_draft_ledger.jsonl"
    ),
    host=args.host,
    port=args.port,
)
