from pathlib import Path
from live_approval.io import load_json

def payload(root:Path)->dict:
    return load_json(root/"release/v166_01_to_v170_64/actual/live_read_only_approval_result.json")
