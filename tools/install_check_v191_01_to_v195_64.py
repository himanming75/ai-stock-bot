from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"production_scheduler/io.py","production_scheduler/config.py","production_scheduler/lock.py",
"production_scheduler/jobs.py","production_scheduler/plan.py","production_scheduler/engine.py",
"production_scheduler/dashboard.py","web_controller/production_scheduler_api.py",
"tools/run_v191_01_to_v195_64.py","tools/test_v191_01_to_v195_64.py",
"tools/verify_v191_01_to_v195_64.py",
"release/v191_01_to_v195_64/config/production_scheduler_policy.json",
"release/v191_01_to_v195_64/scheduler/INSTALL_PRODUCTION_SCHEDULED_TASKS.ps1",
"release/v191_01_to_v195_64/scheduler/REMOVE_PRODUCTION_SCHEDULED_TASKS.ps1",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V191.01-V195.64 INSTALL CHECK PASS")
