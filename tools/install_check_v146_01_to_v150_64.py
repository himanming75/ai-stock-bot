from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=["strategy_manager/io.py","strategy_manager/config.py","strategy_manager/apply.py","strategy_manager/dashboard.py","web_controller/strategy_api.py","web_controller/server.py","web_controller/static/index.html","web_controller/static/style.css","web_controller/static/app.js","release/v146_01_to_v150_64/config/strategy_manager.json","tools/test_v146_01_to_v150_64.py","tools/verify_v146_01_to_v150_64.py"]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V146.01-V150.64 INSTALL CHECK PASS")
