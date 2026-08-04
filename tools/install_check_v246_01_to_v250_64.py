from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "ai_strategy_ensemble_v3/io.py",
    "ai_strategy_ensemble_v3/config.py",
    "ai_strategy_ensemble_v3/regime.py",
    "ai_strategy_ensemble_v3/scoring.py",
    "ai_strategy_ensemble_v3/allocation.py",
    "ai_strategy_ensemble_v3/decision.py",
    "ai_strategy_ensemble_v3/gate.py",
    "ai_strategy_ensemble_v3/engine.py",
    "ai_strategy_ensemble_v3/dashboard.py",
    "web_controller/strategy_ensemble_v3_api.py",
    "tools/run_v246_01_to_v250_64.py",
    "tools/test_v246_01_to_v250_64.py",
    "tools/verify_v246_01_to_v250_64.py",
    "release/v246_01_to_v250_64/config/ai_strategy_ensemble_v3_policy.json",
    "release/v246_01_to_v250_64/docs/AI_STRATEGY_ENSEMBLE_V3_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for x in missing:
    print("MISSING:", x)
if missing:
    raise SystemExit(1)
print("V246.01-V250.64 INSTALL CHECK PASS")
