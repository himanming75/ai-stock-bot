from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_platform.service import (
    run_bundle_b_offline_qualification,
)

result = run_bundle_b_offline_qualification(ROOT)
actual = (
    ROOT / "release/bundle_b_r11_to_r13_broker_multi_account/actual"
)
actual.mkdir(parents=True, exist_ok=True)
(actual / "bundle_b_result.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
