from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path


def create_token(output_path: Path, ticket_snapshot_sha256: str) -> dict:
    token = {
        "purpose": "paper-submit",
        "nonce": secrets.token_hex(16),
        "ticket_snapshot_sha256": ticket_snapshot_sha256,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=10)
        ).isoformat(),
        "used": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(token, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return token


def validate_token(
    token_path: Path,
    ticket_snapshot_sha256: str,
    expected_nonce: str,
) -> tuple[dict | None, list[str]]:
    blockers = []
    if not token_path.exists():
        return None, ["APPROVAL_TOKEN_MISSING"]

    token = json.loads(token_path.read_text(encoding="utf-8"))
    if token.get("purpose") != "paper-submit":
        blockers.append("INVALID_TOKEN_PURPOSE")
    if token.get("used") is True:
        blockers.append("APPROVAL_TOKEN_ALREADY_USED")
    if token.get("nonce") != expected_nonce:
        blockers.append("APPROVAL_NONCE_MISMATCH")
    if token.get("ticket_snapshot_sha256") != ticket_snapshot_sha256:
        blockers.append("TICKET_SNAPSHOT_HASH_MISMATCH")

    expires_at = datetime.fromisoformat(token["expires_at"])
    if datetime.now(timezone.utc) >= expires_at:
        blockers.append("APPROVAL_TOKEN_EXPIRED")

    return token, blockers


def consume_token(token_path: Path, token: dict) -> None:
    token["used"] = True
    token["used_at"] = datetime.now(timezone.utc).isoformat()
    token_path.write_text(
        json.dumps(token, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
