from argparse import ArgumentParser
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configuration_profiles.loader import load_profile
from runtime_configuration.binding import bind_profile_to_runtime
from runtime_configuration.environment import build_environment_preview

parser = ArgumentParser()
parser.add_argument("--profile", required=True)
args = parser.parse_args()

profile_path = (
    ROOT / "release/r4_configuration_profiles/config/profiles"
         / args.profile
)
profile, validation = load_profile(profile_path)
if not validation["valid"]:
    raise SystemExit("INVALID_PROFILE")

runtime = bind_profile_to_runtime(profile)
result = {
    "stage": "R5_ENVIRONMENT_PREVIEW",
    "profile_name": runtime.profile_name,
    "environment": build_environment_preview(runtime),
    "actual_environment_modified": False,
    "broker_network_used": False,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
