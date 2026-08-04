from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"multi_broker_production/io.py","multi_broker_production/config.py",
"multi_broker_production/registry.py","multi_broker_production/snapshots.py",
"multi_broker_production/health.py","multi_broker_production/portfolio.py",
"multi_broker_production/failover.py","multi_broker_production/risk.py",
"multi_broker_production/engine.py","multi_broker_production/dashboard.py",
"web_controller/multi_broker_api.py","tools/run_v196_01_to_v200_64.py",
"tools/test_v196_01_to_v200_64.py","tools/verify_v196_01_to_v200_64.py",
"release/v196_01_to_v200_64/config/multi_broker_policy.json",
"release/v196_01_to_v200_64/config/multi_broker_registry.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V196.01-V200.64 INSTALL CHECK PASS")
