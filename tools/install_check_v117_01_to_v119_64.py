from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"live_safety_system/io.py",
"live_safety_system/kill_switch.py",
"live_safety_system/loss_limits.py",
"live_safety_system/exposure.py",
"live_safety_system/anomaly.py",
"live_safety_system/emergency.py",
"live_safety_system/resume.py",
"live_safety_system/certificate.py",
"live_safety_system/engine.py",
"live_safety_system/dashboard.py",
"tools/run_v117_01_to_v119_64.py",
"tools/test_v117_01_to_v119_64.py",
"tools/verify_v117_01_to_v119_64.py",
"release/v117_01_to_v119_64/input/live_safety_policy.json",
"release/v117_01_to_v119_64/input/safety_telemetry_fixture.json",
"release/v117_01_to_v119_64/docs/EMERGENCY_OPERATIONS_GUIDE.md",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)
print("V117.01-V119.64 INSTALL CHECK PASS")
