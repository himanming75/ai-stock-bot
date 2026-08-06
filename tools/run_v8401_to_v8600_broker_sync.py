from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_sync.service import (
    BrokerSyncCertificationService,
)

result = BrokerSyncCertificationService().evaluate(
    output_dir=Path(
        "release/v8401_8600_broker_sync"
    )
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(
    0 if result["status"] == "PASS" else 2
)
