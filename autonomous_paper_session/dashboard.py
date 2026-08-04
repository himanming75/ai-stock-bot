from pathlib import Path
from autonomous_paper_session.io import load_json

def payload(root: Path) -> dict:
    return load_json(root / "release/v261_01_to_v265_64/actual/session_runner_result.json")
