from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio_optimizer_ai.dashboard import run_dashboard

parser = argparse.ArgumentParser()
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8776)
args = parser.parse_args()

run_dashboard(
    args.host,
    args.port,
    Path("release/v13001_14000_portfolio_optimizer"),
)
