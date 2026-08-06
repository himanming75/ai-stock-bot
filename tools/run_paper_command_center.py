from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_command_center.config import (
    default_paths,
)
from paper_command_center.web import serve


parser = argparse.ArgumentParser()
parser.add_argument(
    "--host",
    default="127.0.0.1",
)
parser.add_argument(
    "--port",
    type=int,
    default=8769,
)
args = parser.parse_args()

serve(
    paths=default_paths(),
    host=args.host,
    port=args.port,
)
