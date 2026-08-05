from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deployment.readiness import evaluate_deployment_readiness

result = evaluate_deployment_readiness(ROOT)
actual = ROOT / "release/r1_production_deployment_preparation/actual"
actual.mkdir(parents=True, exist_ok=True)
(actual / "r1_readiness_result.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
(actual / "release_manifest.json").write_text(
    json.dumps(result["release_manifest"], indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
(actual / "backup_inventory.json").write_text(
    json.dumps(result["backup_inventory"], indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
