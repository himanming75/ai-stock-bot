from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deployment.certificate import generate_release_certificate

result = generate_release_certificate(ROOT)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["eligible"] else 2)
