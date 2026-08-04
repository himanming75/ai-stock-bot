from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"live_approval/io.py","live_approval/config.py","live_approval/credentials.py",
"live_approval/snapshot.py","live_approval/comparison.py","live_approval/approval.py",
"live_approval/engine.py","live_approval/dashboard.py",
"web_controller/live_approval_api.py","tools/run_v166_01_to_v170_64.py",
"tools/test_v166_01_to_v170_64.py","tools/verify_v166_01_to_v170_64.py",
"release/v166_01_to_v170_64/config/live_approval_policy.json",
"release/v166_01_to_v170_64/input/live_readonly_fixture.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V166.01-V170.64 INSTALL CHECK PASS")
