from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from configuration_profiles.catalog import build_profile_catalog

profile_dir = (
    ROOT / "release/r4_configuration_profiles/config/profiles"
)
result = build_profile_catalog(profile_dir)
actual = ROOT / "release/r4_configuration_profiles/actual"
actual.mkdir(parents=True, exist_ok=True)
(actual / "profile_catalog.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["all_profiles_valid"] else 1)
