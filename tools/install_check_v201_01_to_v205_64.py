from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"broker_plugins/io.py","broker_plugins/spec.py","broker_plugins/discovery.py",
"broker_plugins/compatibility.py","broker_plugins/capabilities.py",
"broker_plugins/loader.py","broker_plugins/reload.py","broker_plugins/engine.py",
"broker_plugins/dashboard.py","web_controller/broker_plugins_api.py",
"tools/run_v201_01_to_v205_64.py","tools/test_v201_01_to_v205_64.py",
"tools/verify_v201_01_to_v205_64.py",
"broker_plugin_packages/alpaca_paper/manifest.json",
"broker_plugin_packages/alpaca_live_readonly/manifest.json",
"broker_plugin_packages/etrade/manifest.json",
"broker_plugin_packages/ibkr/manifest.json",
"broker_plugin_packages/schwab/manifest.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
print("V201.01-V205.64 INSTALL CHECK PASS")
