from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from observation_governance.engine import govern

parser = argparse.ArgumentParser()
parser.add_argument("--qualification-path")
parser.add_argument("--no-persist", action="store_true")
args = parser.parse_args()

qpath = Path(args.qualification_path) if args.qualification_path else None
if qpath is not None and not qpath.is_absolute():
    qpath = ROOT / qpath

result = govern(ROOT, qualification_path=qpath, persist=not args.no_persist)
print(json.dumps(result, indent=2, sort_keys=True))
