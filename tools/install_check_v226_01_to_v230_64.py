from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "live_shadow_slippage/io.py",
    "live_shadow_slippage/config.py",
    "live_shadow_slippage/quote.py",
    "live_shadow_slippage/slippage.py",
    "live_shadow_slippage/qualification.py",
    "live_shadow_slippage/report.py",
    "live_shadow_slippage/engine.py",
    "live_shadow_slippage/dashboard.py",
    "web_controller/live_shadow_api.py",
    "tools/run_v226_01_to_v230_64.py",
    "tools/test_v226_01_to_v230_64.py",
    "tools/verify_v226_01_to_v230_64.py",
    "release/v226_01_to_v230_64/config/live_shadow_policy.json",
    "release/v226_01_to_v230_64/docs/LIVE_SHADOW_SLIPPAGE_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for path in missing:
    print("MISSING:", path)
if missing:
    raise SystemExit(1)
print("V226.01-V230.64 INSTALL CHECK PASS")
