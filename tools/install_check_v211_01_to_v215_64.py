from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"ai_strategy_ensemble/io.py","ai_strategy_ensemble/config.py","ai_strategy_ensemble/scoring.py",
"ai_strategy_ensemble/ranking.py","ai_strategy_ensemble/allocation.py","ai_strategy_ensemble/signal.py",
"ai_strategy_ensemble/engine.py","ai_strategy_ensemble/dashboard.py",
"web_controller/strategy_ensemble_api.py","tools/run_v211_01_to_v215_64.py",
"tools/test_v211_01_to_v215_64.py","tools/verify_v211_01_to_v215_64.py",
"release/v211_01_to_v215_64/config/ai_strategy_ensemble_policy.json",
"release/v211_01_to_v215_64/input/strategy_performance.json",
"release/v211_01_to_v215_64/input/strategy_signals.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V211.01-V215.64 INSTALL CHECK PASS")
