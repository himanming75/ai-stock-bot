from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / "real_paper_data_collection/collector.py",
    ROOT / "release/v311_01_to_v320_64/config/real_paper_data_collection_policy.json",
    ROOT / "long_run_qualification/config.py",
    ROOT / "long_run_qualification/runner.py",
    ROOT / "long_run_qualification/qualifier.py",
    ROOT / "release/v321_01_to_v330_64/config/real_paper_long_run_policy.json",
]
missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
result = {"stage":"V330.64","status":"PASS" if not missing else "FAIL","missing":missing,"actual_paper_orders_submitted":0,"actual_live_orders_submitted":0}
print(json.dumps(result, indent=2))
raise SystemExit(0 if not missing else 1)
