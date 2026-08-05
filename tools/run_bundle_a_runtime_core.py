from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_core.service import run_offline_bundle_qualification

result = run_offline_bundle_qualification(ROOT)
actual = ROOT / "release/bundle_a_r7_to_r10_runtime_core/actual"
actual.mkdir(parents=True, exist_ok=True)
(actual / "bundle_a_result.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
