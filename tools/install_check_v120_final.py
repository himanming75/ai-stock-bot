from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"v120_final_release/io.py","v120_final_release/integration.py",
"v120_final_release/safety.py","v120_final_release/inventory.py",
"v120_final_release/bundle.py","v120_final_release/engine.py",
"v120_final_release/dashboard.py","tools/run_v120_final.py",
"tools/test_v120_final.py","tools/verify_v120_final.py",
"release/v120_final/input/v120_release_policy.json",
"release/v120_final/docs/FINAL_OPERATOR_GUIDE.md",
"release/v120_final/rollback/RESTORE_TO_V119.ps1",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
print("V120 FINAL INSTALL CHECK PASS")
