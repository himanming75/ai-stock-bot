from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_feature_engine.service import AIFeatureSignalCertificationService

result = AIFeatureSignalCertificationService().evaluate(
    output_dir=Path("release/v9801_10400_ai_feature_signal")
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 2)
