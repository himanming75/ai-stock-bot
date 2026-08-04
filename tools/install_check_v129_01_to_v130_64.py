from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"restricted_live_candidate/io.py","restricted_live_candidate/account.py",
"restricted_live_candidate/candidates.py","restricted_live_candidate/gate.py",
"restricted_live_candidate/reconcile.py","restricted_live_candidate/gateway.py",
"restricted_live_candidate/engine.py","restricted_live_candidate/dashboard.py",
"tools/run_v129_01_to_v130_64.py","tools/test_v129_01_to_v130_64.py",
"tools/verify_v129_01_to_v130_64.py",
"release/v129_01_to_v130_64/input/restricted_live_candidate_policy.json",
"release/v129_01_to_v130_64/input/live_readonly_fixture.json",
"release/v129_01_to_v130_64/docs/RESTRICTED_LIVE_CANDIDATE_GUIDE.md",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V129.01-V130.64 INSTALL CHECK PASS")
