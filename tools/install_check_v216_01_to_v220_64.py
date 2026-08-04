from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"final_production_release/io.py","final_production_release/config.py",
"final_production_release/inventory.py","final_production_release/integration.py",
"final_production_release/integrity.py","final_production_release/certificate.py",
"final_production_release/bundle.py","final_production_release/engine.py",
"final_production_release/dashboard.py","web_controller/final_release_api.py",
"tools/run_v216_01_to_v220_64.py","tools/test_v216_01_to_v220_64.py",
"tools/verify_v216_01_to_v220_64.py",
"release/v216_01_to_v220_64/config/final_production_release_policy.json",
"release/v216_01_to_v220_64/docs/FINAL_OPERATOR_GUIDE.md",
"release/v216_01_to_v220_64/rollback/RESTORE_TO_V215.ps1",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V216.01-V220.64 INSTALL CHECK PASS")
