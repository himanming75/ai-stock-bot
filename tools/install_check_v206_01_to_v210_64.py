from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"risk_engine_v2/io.py","risk_engine_v2/config.py","risk_engine_v2/metrics.py",
"risk_engine_v2/kill_switch.py","risk_engine_v2/gate.py","risk_engine_v2/engine.py",
"risk_engine_v2/dashboard.py","web_controller/risk_v2_api.py",
"tools/run_v206_01_to_v210_64.py","tools/test_v206_01_to_v210_64.py",
"tools/verify_v206_01_to_v210_64.py",
"release/v206_01_to_v210_64/config/risk_engine_v2_policy.json",
"release/v206_01_to_v210_64/control/risk_kill_switch.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V206.01-V210.64 INSTALL CHECK PASS")
