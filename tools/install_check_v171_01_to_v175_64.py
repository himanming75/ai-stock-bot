from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"controlled_micro_live/io.py","controlled_micro_live/config.py",
"controlled_micro_live/kill_switch.py","controlled_micro_live/token.py",
"controlled_micro_live/dry_run.py","controlled_micro_live/reconcile.py",
"controlled_micro_live/engine.py","controlled_micro_live/dashboard.py",
"web_controller/micro_live_api.py","tools/run_v171_01_to_v175_64.py",
"tools/test_v171_01_to_v175_64.py","tools/verify_v171_01_to_v175_64.py",
"release/v171_01_to_v175_64/config/controlled_micro_live_policy.json",
"release/v171_01_to_v175_64/control/micro_live_kill_switch.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V171.01-V175.64 INSTALL CHECK PASS")
