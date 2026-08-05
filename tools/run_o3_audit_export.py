from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from operations.audit_export import export_audit

result = export_audit(
    ROOT,
    ROOT / "release/o3_autonomous_operations/actual/export",
)
print(json.dumps(result, indent=2, sort_keys=True))
