from argparse import ArgumentParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_configuration.service import (
    write_runtime_bridge_preview,
)

parser = ArgumentParser()
parser.add_argument("--profile", required=True)
args = parser.parse_args()

profile_path = (
    ROOT / "release/r4_configuration_profiles/config/profiles"
         / args.profile
)
if not profile_path.exists():
    raise SystemExit(f"PROFILE_NOT_FOUND:{profile_path}")

result = write_runtime_bridge_preview(ROOT, profile_path)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result.get("status") == "PASS" else 1)
