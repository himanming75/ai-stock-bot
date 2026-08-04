from __future__ import annotations
from pathlib import Path
from long_run_qualification.io import load_json
from long_run_qualification.qualifier import qualify


def get_status(root: Path) -> dict:
    return qualify(root)


def get_session_summary(root: Path) -> dict:
    return load_json(root / "release/v321_01_to_v330_64/actual/real_paper_long_run_session_summary.json", {})
