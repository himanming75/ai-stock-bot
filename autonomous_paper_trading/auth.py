from __future__ import annotations
import os
from pathlib import Path
from autonomous_paper_trading.io import load_json

def credentials() -> dict:
    key = os.getenv("ALPACA_PAPER_API_KEY") or os.getenv("APCA_API_KEY_ID") or ""
    secret = os.getenv("ALPACA_PAPER_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY") or ""
    return {"key": key, "secret": secret, "ready": bool(key and secret)}

def confirmation(root: Path, policy: dict) -> dict:
    path = root / "release/v256_01_to_v260_64/control/autonomous_paper_confirmation.json"
    value = load_json(path)
    valid = (
        value.get("enabled") is True
        and value.get("phrase") == policy.get("confirmation_phrase")
    )
    return {"valid": valid, "value": value}
