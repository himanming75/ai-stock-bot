from __future__ import annotations

from pathlib import Path
from typing import Any

from .readers import read_json


def read_auto_validation_status(root: Path) -> dict[str, Any]:
    return read_json(
        root / "runtime/market_open_auto_validation/latest_status.json"
    )
