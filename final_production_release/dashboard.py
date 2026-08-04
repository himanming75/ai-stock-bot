from pathlib import Path
from final_production_release.io import load_json

def payload(root:Path)->dict:
    return load_json(root/"release/v216_01_to_v220_64/actual/v220_final_production_result.json")
