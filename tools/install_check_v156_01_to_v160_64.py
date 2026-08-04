from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"operations_manager/io.py","operations_manager/config.py","operations_manager/lock.py",
"operations_manager/notifications.py","operations_manager/health.py",
"operations_manager/recovery.py","operations_manager/jobs.py","operations_manager/state.py",
"web_controller/operations_api.py","web_controller/server.py",
"web_controller/static/index.html","web_controller/static/style.css","web_controller/static/app.js",
"tools/run_v156_operations_job.py","tools/test_v156_01_to_v160_64.py",
"tools/verify_v156_01_to_v160_64.py",
"release/v156_01_to_v160_64/config/operations_manager.json",
"release/v156_01_to_v160_64/scheduler/INSTALL_SAFE_SCHEDULED_TASKS.ps1",
"release/v156_01_to_v160_64/scheduler/REMOVE_SAFE_SCHEDULED_TASKS.ps1",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V156.01-V160.64 INSTALL CHECK PASS")
