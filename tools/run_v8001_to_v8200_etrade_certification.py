from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etrade_sandbox.service import (
    ETradeSandboxCertificationService,
)

result = ETradeSandboxCertificationService().evaluate(
    output_dir=Path(
        "release/v8001_8200_etrade_sandbox/actual"
    )
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(
    0 if result["status"] == "PASS" else 2
)
