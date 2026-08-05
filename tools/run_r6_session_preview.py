from argparse import ArgumentParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_session.service import create_preview_session

parser = ArgumentParser()
parser.add_argument("--profile", required=True)
args = parser.parse_args()

profile_path = (
    ROOT / "release/r4_configuration_profiles/config/profiles"
         / args.profile
)
result = create_preview_session(ROOT, profile_path)
actual = ROOT / "release/r6_runtime_session_manager/actual"
actual.mkdir(parents=True, exist_ok=True)
(actual / "last_session_preview.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
