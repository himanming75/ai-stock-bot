from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"portfolio_broker/io.py","portfolio_broker/models.py","portfolio_broker/base.py",
"portfolio_broker/adapters.py","portfolio_broker/registry.py","portfolio_broker/portfolio.py",
"portfolio_broker/risk.py","portfolio_broker/engine.py","portfolio_broker/dashboard.py",
"web_controller/portfolio_api.py","tools/run_v181_01_to_v185_64.py",
"tools/test_v181_01_to_v185_64.py","tools/verify_v181_01_to_v185_64.py",
"release/v181_01_to_v185_64/config/broker_registry.json",
"release/v181_01_to_v185_64/config/portfolio_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V181.01-V185.64 INSTALL CHECK PASS")
