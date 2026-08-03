from __future__ import annotations
from pathlib import Path
from typing import Any
from automated_backtest.io import load_json, write_json

def cache_path(root: Path, job_id: str) -> Path:
    return (
        root
        / "release/v98_01_to_v98_32/actual/cache"
        / f"{job_id}.json"
    )

def read_cached(root: Path, job_id: str) -> dict[str, Any]:
    return load_json(cache_path(root, job_id))

def write_cached(root: Path, job_id: str, result: dict[str, Any]) -> None:
    write_json(cache_path(root, job_id), result)
