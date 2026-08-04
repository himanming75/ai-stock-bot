from pathlib import Path
from ai_strategy_ensemble.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v211_01_to_v215_64/actual/ai_strategy_ensemble_result.json")
