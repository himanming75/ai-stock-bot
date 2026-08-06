from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_command_center.service import (
    PaperCommandCenterCertificationService,
)

result = (
    PaperCommandCenterCertificationService()
    .evaluate(
        output_dir=Path(
            "release/v8801_9000_paper_command_center/actual"
        )
    )
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(
    0 if result["status"] == "PASS" else 2
)
