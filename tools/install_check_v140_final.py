from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"v140_autonomous_release/io.py",
"v140_autonomous_release/integration.py",
"v140_autonomous_release/safety.py",
"v140_autonomous_release/certificate.py",
"v140_autonomous_release/engine.py",
"v140_autonomous_release/dashboard.py",
"tools/run_v140_final.py",
"tools/test_v140_final.py",
"tools/verify_v140_final.py",
"release/v140_final/input/v140_release_policy.json",
"release/v140_final/docs/V140_FINAL_OPERATOR_GUIDE.md",
"release/v140_final/rollback/RESTORE_TO_V139.ps1",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
print("V140 FINAL INSTALL CHECK PASS")
