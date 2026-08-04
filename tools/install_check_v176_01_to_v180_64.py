from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 "restricted_live_automation/io.py","restricted_live_automation/config.py",
 "restricted_live_automation/gate.py","restricted_live_automation/plan.py",
 "restricted_live_automation/engine.py","restricted_live_automation/dashboard.py",
 "web_controller/restricted_live_api.py","tools/run_v176_01_to_v180_64.py",
 "tools/test_v176_01_to_v180_64.py","tools/verify_v176_01_to_v180_64.py",
 "release/v176_01_to_v180_64/config/restricted_live_automation_policy.json"
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V176.01-V180.64 INSTALL CHECK PASS")
