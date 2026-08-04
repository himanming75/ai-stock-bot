from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "multi_timeframe_strategy/io.py",
    "multi_timeframe_strategy/config.py",
    "multi_timeframe_strategy/timeframes.py",
    "multi_timeframe_strategy/scoring.py",
    "multi_timeframe_strategy/conflicts.py",
    "multi_timeframe_strategy/voting.py",
    "multi_timeframe_strategy/allocation.py",
    "multi_timeframe_strategy/engine.py",
    "multi_timeframe_strategy/dashboard.py",
    "web_controller/multi_timeframe_strategy_api.py",
    "tools/run_v271_01_to_v280_64.py",
    "tools/test_v271_01_to_v280_64.py",
    "tools/verify_v271_01_to_v280_64.py",
    "release/v271_01_to_v280_64/config/multi_timeframe_strategy_policy.json",
    "release/v271_01_to_v280_64/docs/MULTI_TIMEFRAME_STRATEGY_ENSEMBLE_GUIDE.md",
]
missing = [item for item in required if not (ROOT / item).exists()]
for item in missing:
    print("MISSING:", item)
if missing:
    raise SystemExit(1)
print("V271.01-V280.64 INSTALL CHECK PASS")
