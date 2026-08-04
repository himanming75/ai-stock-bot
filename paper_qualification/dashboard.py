from pathlib import Path
from paper_qualification.io import load_json

def payload(root:Path)->dict:
    return load_json(root/"release/v161_01_to_v165_64/actual/paper_qualification_result.json")
