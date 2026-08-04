from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"dynamic_live_risk/io.py","dynamic_live_risk/sizing.py",
"dynamic_live_risk/budget.py","dynamic_live_risk/exposure.py",
"dynamic_live_risk/loss_limits.py","dynamic_live_risk/concentration.py",
"dynamic_live_risk/certificate.py","dynamic_live_risk/engine.py",
"dynamic_live_risk/dashboard.py","tools/run_v134_01_to_v136_64.py",
"tools/test_v134_01_to_v136_64.py","tools/verify_v134_01_to_v136_64.py",
"release/v134_01_to_v136_64/input/dynamic_live_risk_policy.json",
"release/v134_01_to_v136_64/input/dynamic_live_risk_fixture.json",
"release/v134_01_to_v136_64/docs/DYNAMIC_LIVE_RISK_GUIDE.md",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V134.01-V136.64 INSTALL CHECK PASS")
