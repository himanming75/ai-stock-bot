from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=["paper_web_ops/io.py","paper_web_ops/settings.py","paper_web_ops/state.py","paper_web_ops/runner.py","web_controller/paper_api.py","web_controller/server.py","web_controller/static/index.html","web_controller/static/style.css","web_controller/static/app.js","release/v151_01_to_v155_64/config/paper_web_operations.json","tools/test_v151_01_to_v155_64.py","tools/verify_v151_01_to_v155_64.py"]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V151.01-V155.64 INSTALL CHECK PASS")
