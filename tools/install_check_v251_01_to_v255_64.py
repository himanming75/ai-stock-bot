from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "execution_optimizer/io.py",
    "execution_optimizer/config.py",
    "execution_optimizer/quote_analyzer.py",
    "execution_optimizer/fill_probability.py",
    "execution_optimizer/slippage.py",
    "execution_optimizer/planner.py",
    "execution_optimizer/retry_manager.py",
    "execution_optimizer/engine.py",
    "execution_optimizer/dashboard.py",
    "web_controller/execution_optimizer_api.py",
    "tools/run_v251_01_to_v255_64.py",
    "tools/test_v251_01_to_v255_64.py",
    "tools/verify_v251_01_to_v255_64.py",
    "release/v251_01_to_v255_64/config/execution_optimizer_policy.json",
    "release/v251_01_to_v255_64/docs/EXECUTION_OPTIMIZER_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for x in missing:
    print("MISSING:", x)
if missing:
    raise SystemExit(1)
print("V251.01-V255.64 INSTALL CHECK PASS")
