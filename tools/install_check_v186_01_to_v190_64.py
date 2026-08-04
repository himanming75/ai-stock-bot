from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"production_operations/io.py","production_operations/config.py",
"production_operations/reporting.py","production_operations/health.py",
"production_operations/backup.py","production_operations/certificate.py",
"production_operations/engine.py","production_operations/dashboard.py",
"web_controller/production_api.py","tools/run_v186_01_to_v190_64.py",
"tools/test_v186_01_to_v190_64.py","tools/verify_v186_01_to_v190_64.py",
"release/v186_01_to_v190_64/config/production_operations_policy.json",
"release/v186_01_to_v190_64/docs/PRODUCTION_OPERATIONS_GUIDE.md",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V186.01-V190.64 INSTALL CHECK PASS")
