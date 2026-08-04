from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"paper_qualification/io.py","paper_qualification/config.py","paper_qualification/source.py",
"paper_qualification/metrics.py","paper_qualification/strategies.py","paper_qualification/windows.py",
"paper_qualification/engine.py","paper_qualification/dashboard.py",
"web_controller/qualification_api.py","tools/run_v161_01_to_v165_64.py",
"tools/test_v161_01_to_v165_64.py","tools/verify_v161_01_to_v165_64.py",
"release/v161_01_to_v165_64/config/paper_qualification_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V161.01-V165.64 INSTALL CHECK PASS")
