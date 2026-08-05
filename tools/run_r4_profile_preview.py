from argparse import ArgumentParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configuration_profiles.loader import preview_profile_activation

parser = ArgumentParser()
parser.add_argument("--profile", required=True)
args = parser.parse_args()

profile_path = (
    ROOT / "release/r4_configuration_profiles/config/profiles"
         / args.profile
)
if not profile_path.exists():
    raise SystemExit(f"PROFILE_NOT_FOUND:{profile_path}")

result = preview_profile_activation(ROOT, profile_path)
actual = ROOT / "release/r4_configuration_profiles/actual"
actual.mkdir(parents=True, exist_ok=True)
(actual / "last_profile_preview.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
