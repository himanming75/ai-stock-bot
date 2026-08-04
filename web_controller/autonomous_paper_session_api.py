from pathlib import Path
from autonomous_paper_session.dashboard import payload

def get_payload(root: Path) -> dict:
    return payload(root)
