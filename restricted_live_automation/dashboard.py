from pathlib import Path
from restricted_live_automation.io import load_json
def payload(root:Path)->dict:
    return load_json(root/"release/v176_01_to_v180_64/actual/restricted_live_automation_result.json")
