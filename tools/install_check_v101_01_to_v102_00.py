from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_engine import EventBus, RuntimeConfig, Scheduler

RuntimeConfig().validate()
assert EventBus
assert Scheduler

source = ROOT / "release" / "v100_00" / "output" / "v100_completion_certificate.json"
if not source.is_file():
    raise SystemExit(f"MISSING V100 SOURCE CERTIFICATE: {source}")

print("V101.01-V102.00 RUNTIME FOUNDATION INSTALL CHECK PASS")
