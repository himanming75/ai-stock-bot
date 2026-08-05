from __future__ import annotations
import hashlib, json, secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def create_token(output_path: Path, plan_sha256: str) -> dict:
    now = datetime.now(timezone.utc)
    token = {
        "purpose": "p3-paper-reject-validation",
        "nonce": secrets.token_hex(16),
        "plan_sha256": plan_sha256,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
        "used": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(token, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return token

def validate_token(token_path: Path, plan_sha256: str, nonce: str):
    if not token_path.exists():
        return None, ["APPROVAL_TOKEN_MISSING"]
    token = json.loads(token_path.read_text(encoding="utf-8"))
    blockers = []
    if token.get("purpose") != "p3-paper-reject-validation":
        blockers.append("INVALID_TOKEN_PURPOSE")
    if token.get("used"):
        blockers.append("TOKEN_ALREADY_USED")
    if token.get("nonce") != nonce:
        blockers.append("NONCE_MISMATCH")
    if token.get("plan_sha256") != plan_sha256:
        blockers.append("PLAN_HASH_MISMATCH")
    if datetime.now(timezone.utc) >= datetime.fromisoformat(token["expires_at"]):
        blockers.append("TOKEN_EXPIRED")
    return token, sorted(set(blockers))

def consume_token(token_path: Path, token: dict) -> None:
    token["used"] = True
    token["used_at"] = datetime.now(timezone.utc).isoformat()
    token_path.write_text(json.dumps(token, indent=2, sort_keys=True) + "\n", encoding="utf-8")
