from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"controlled_micro_live/io.py","controlled_micro_live/approval.py",
"controlled_micro_live/token.py","controlled_micro_live/kill_switch.py",
"controlled_micro_live/payload.py","controlled_micro_live/simulator.py",
"controlled_micro_live/review.py","controlled_micro_live/engine.py",
"controlled_micro_live/dashboard.py","tools/run_v131_01_to_v133_64.py",
"tools/test_v131_01_to_v133_64.py","tools/verify_v131_01_to_v133_64.py",
"release/v131_01_to_v133_64/input/controlled_micro_live_policy.json",
"release/v131_01_to_v133_64/docs/CONTROLLED_MICRO_LIVE_REVIEW_GUIDE.md",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V131.01-V133.64 INSTALL CHECK PASS")
