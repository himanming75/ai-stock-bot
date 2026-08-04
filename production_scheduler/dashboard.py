from pathlib import Path
from production_scheduler.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v191_01_to_v195_64/actual/production_scheduler_result.json")
