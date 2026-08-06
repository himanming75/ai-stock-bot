from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase1_premarket_completion.service import (
    Phase1PremarketCompletionService,
)

result = Phase1PremarketCompletionService().evaluate(
    output_dir=Path(
        "release/v9201_9800_phase1_premarket_completion"
    )
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(
    0 if result["status"] == "PASS" else 2
)
