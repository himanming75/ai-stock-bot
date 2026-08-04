from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"micro_live_readiness/io.py","micro_live_readiness/candidates.py",
"micro_live_readiness/limits.py","micro_live_readiness/approval.py",
"micro_live_readiness/token.py","micro_live_readiness/gateway.py",
"micro_live_readiness/shadow_compare.py","micro_live_readiness/engine.py",
"micro_live_readiness/dashboard.py","tools/run_v127_01_to_v128_64.py",
"tools/test_v127_01_to_v128_64.py","tools/verify_v127_01_to_v128_64.py",
"release/v127_01_to_v128_64/input/micro_live_readiness_policy.json",
"release/v127_01_to_v128_64/docs/MICRO_LIVE_OPERATOR_GUIDE.md",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V127.01-V128.64 INSTALL CHECK PASS")
