from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "continuous_service_runtime/io.py",
    "continuous_service_runtime/state_machine.py",
    "continuous_service_runtime/heartbeat.py",
    "continuous_service_runtime/scheduler.py",
    "continuous_service_runtime/checkpoint.py",
    "continuous_service_runtime/recovery.py",
    "continuous_service_runtime/shutdown.py",
    "continuous_service_runtime/runtime.py",
    "continuous_service_runtime/dashboard.py",
    "tools/run_v104_33_to_v104_64.py",
    "tools/test_v104_33_to_v104_64.py",
    "tools/verify_v104_33_to_v104_64.py",
    "release/v104_33_to_v104_64/input/continuous_runtime_policy.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)

print("V104.33-V104.64 INSTALL CHECK PASS")
