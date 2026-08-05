from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from actual_environment.certificate import (
    build_certificate,
    write_json,
)
from actual_environment.qualification import qualify

result = qualify(ROOT)
actual = (
    ROOT / "release/p1_actual_environment_qualification/actual"
)
write_json(actual / "p1_actual_environment_result.json", result)
certificate = build_certificate(result)
write_json(actual / "p1_actual_environment_certificate.json", certificate)

print(json.dumps(result, indent=2, sort_keys=True))
print("=== P1 CERTIFICATE ===")
print(json.dumps(certificate, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
