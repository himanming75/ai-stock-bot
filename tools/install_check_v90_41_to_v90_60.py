from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_market_data.actual_paper_runtime_certification_v90_41_60 import (
    ActualPaperRuntimeCertificationConfig,
)

ActualPaperRuntimeCertificationConfig().validate()

required = [
    ROOT / "release/v90_20/output/actual_paper_automation_certificate_v90_20.json",
    ROOT / "release/v90_40/output/read_only_runtime_certificate_v90_40.json",
]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit("MISSING SOURCE CERTIFICATES: " + ", ".join(missing))

print("V90.41-V90.60 INSTALL CHECK PASS")
