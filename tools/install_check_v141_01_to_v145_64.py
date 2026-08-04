from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"web_controller/io.py","web_controller/state.py","web_controller/actions.py",
"web_controller/server.py","web_controller/static/index.html",
"web_controller/static/style.css","web_controller/static/app.js",
"tools/run_v141_01_to_v145_64.py","tools/test_v141_01_to_v145_64.py",
"tools/verify_v141_01_to_v145_64.py",
"release/v141_01_to_v145_64/docs/WEB_CONTROLLER_GUIDE.md",
"release/v141_01_to_v145_64/control/emergency_stop.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V141.01-V145.64 INSTALL CHECK PASS")
