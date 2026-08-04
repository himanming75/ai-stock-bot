from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "position_manager_v2/io.py",
    "position_manager_v2/config.py",
    "position_manager_v2/positions.py",
    "position_manager_v2/exposure.py",
    "position_manager_v2/recovery.py",
    "position_manager_v2/engine.py",
    "position_manager_v2/dashboard.py",
    "web_controller/position_manager_v2_api.py",
    "tools/run_v236_01_to_v240_64.py",
    "tools/test_v236_01_to_v240_64.py",
    "tools/verify_v236_01_to_v240_64.py",
    "release/v236_01_to_v240_64/config/position_manager_v2_policy.json",
    "release/v236_01_to_v240_64/docs/POSITION_MANAGER_V2_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for x in missing:
    print("MISSING:", x)
if missing:
    raise SystemExit(1)
print("V236.01-V240.64 INSTALL CHECK PASS")
