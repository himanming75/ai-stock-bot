#!/usr/bin/env python3
"""
V34.0 Broker Credential Vault Foundation

Security design:
- Never stores raw broker API keys in project files
- Reads credentials only from environment variables
- Returns redacted values and SHA-256 fingerprints only
- Detects suspicious plaintext secret files
- Generates disabled templates containing variable names, not secret values
- Supports broker-specific credential schemas
- Performs no network requests and no broker authentication

This module is a credential reference and audit layer, not an encryption vault.
For production live trading, use an OS or cloud secret manager.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


VERSION = "34.0"


class BrokerName(str, Enum):
    IBKR = "ibkr"
    ALPACA = "alpaca"
    TRADESTATION = "tradestation"


@dataclass(frozen=True)
class CredentialField:
    logical_name: str
    env_var: str
    required: bool
    secret: bool


@dataclass(frozen=True)
class CredentialStatus:
    broker: str
    status: str
    ready: bool
    missing_required: list[str]
    present_fields: list[str]
    redacted: dict[str, str]
    fingerprints: dict[str, str]
    generated_at: str
    network_used: bool


BROKER_SCHEMAS: dict[BrokerName, tuple[CredentialField, ...]] = {
    BrokerName.IBKR: (
        CredentialField("host", "AI_BOT_IBKR_HOST", True, False),
        CredentialField("port", "AI_BOT_IBKR_PORT", True, False),
        CredentialField("client_id", "AI_BOT_IBKR_CLIENT_ID", True, False),
        CredentialField("account_id", "AI_BOT_IBKR_ACCOUNT_ID", False, True),
    ),
    BrokerName.ALPACA: (
        CredentialField("api_key", "AI_BOT_ALPACA_API_KEY", True, True),
        CredentialField("api_secret", "AI_BOT_ALPACA_API_SECRET", True, True),
        CredentialField("base_url", "AI_BOT_ALPACA_BASE_URL", True, False),
    ),
    BrokerName.TRADESTATION: (
        CredentialField("client_id", "AI_BOT_TRADESTATION_CLIENT_ID", True, True),
        CredentialField("client_secret", "AI_BOT_TRADESTATION_CLIENT_SECRET", True, True),
        CredentialField("refresh_token", "AI_BOT_TRADESTATION_REFRESH_TOKEN", True, True),
        CredentialField("account_id", "AI_BOT_TRADESTATION_ACCOUNT_ID", False, True),
    ),
}

SUSPICIOUS_FILE_NAMES = {
    ".env",
    ".env.local",
    "secrets.json",
    "credentials.json",
    "api_keys.json",
    "broker_credentials.json",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|api[_-]?secret|client[_-]?secret|refresh[_-]?token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{12,})"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def redact(value: str, secret: bool) -> str:
    if not value:
        return ""
    if not secret:
        if len(value) <= 6:
            return value
        return value[:3] + "..." + value[-2:]
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + ("*" * max(4, len(value) - 4)) + value[-2:]


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_non_secret(field: CredentialField, value: str) -> str | None:
    if not value:
        return None
    if field.logical_name == "port":
        if not value.isdigit():
            return "port must be numeric"
        port = int(value)
        if not (1 <= port <= 65535):
            return "port must be between 1 and 65535"
    if field.logical_name == "base_url":
        if not value.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            return "base_url must use HTTPS or localhost HTTP"
    if field.logical_name == "client_id" and not field.secret:
        if not re.fullmatch(r"[0-9]{1,10}", value):
            return "client_id must be numeric"
    return None


def inspect_credentials(
    broker: BrokerName,
    environment: Mapping[str, str] | None = None,
) -> CredentialStatus:
    env = environment if environment is not None else os.environ
    missing: list[str] = []
    present: list[str] = []
    redacted: dict[str, str] = {}
    fingerprints: dict[str, str] = {}
    validation_errors: list[str] = []

    for field in BROKER_SCHEMAS[broker]:
        value = str(env.get(field.env_var, "")).strip()
        if not value:
            if field.required:
                missing.append(field.env_var)
            continue

        present.append(field.logical_name)
        redacted[field.logical_name] = redact(value, field.secret)
        fingerprints[field.logical_name] = fingerprint(value)

        if not field.secret:
            error = validate_non_secret(field, value)
            if error:
                validation_errors.append(f"{field.env_var}: {error}")

    ready = not missing and not validation_errors
    status = "READY_REFERENCE_ONLY" if ready else "INCOMPLETE"

    if validation_errors:
        status = "INVALID"

    return CredentialStatus(
        broker=broker.value,
        status=status,
        ready=ready,
        missing_required=missing + validation_errors,
        present_fields=present,
        redacted=redacted,
        fingerprints=fingerprints,
        generated_at=utc_now(),
        network_used=False,
    )


def inspect_all(
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    statuses = {
        broker.value: asdict(inspect_credentials(broker, environment))
        for broker in BrokerName
    }
    return {
        "schema_version": "v34.0.credential_status.1",
        "version": VERSION,
        "status": "PASS",
        "network_used": False,
        "raw_secret_values_included": False,
        "brokers": statuses,
        "generated_at": utc_now(),
    }


def generate_template(path: Path) -> None:
    payload = {
        "schema_version": "v34.0.credential_reference_template.1",
        "version": VERSION,
        "enabled": False,
        "note": (
            "This file contains environment-variable names only. "
            "Do not place API keys or tokens in this file."
        ),
        "brokers": {
            broker.value: {
                field.logical_name: {
                    "env_var": field.env_var,
                    "required": field.required,
                    "secret": field.secret,
                }
                for field in fields
            }
            for broker, fields in BROKER_SCHEMAS.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def scan_for_plaintext_secrets(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0

    excluded_parts = {
        ".git", ".venv", "venv", "__pycache__", "dist", "node_modules",
    }

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in excluded_parts for part in relative.parts):
            continue
        if path.suffix.lower() not in {
            ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".txt", ".md", ""
        } and path.name.lower() not in SUSPICIOUS_FILE_NAMES:
            continue

        scanned += 1
        name_flag = path.name.lower() in SUSPICIOUS_FILE_NAMES
        content_hits: list[str] = []

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                content_hits.append(pattern.pattern[:48])

        if name_flag or content_hits:
            findings.append({
                "path": relative.as_posix(),
                "suspicious_filename": name_flag,
                "pattern_hit_count": len(content_hits),
            })

    return {
        "schema_version": "v34.0.plaintext_secret_scan.1",
        "version": VERSION,
        "status": "PASS" if not findings else "FAIL",
        "scanned_file_count": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "raw_secret_values_included": False,
        "generated_at": utc_now(),
    }


def check_file_permissions(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "MISSING",
            "path": str(path),
        }

    mode = stat.S_IMODE(path.stat().st_mode)
    world_readable = bool(mode & stat.S_IROTH)
    group_readable = bool(mode & stat.S_IRGRP)

    return {
        "status": "PASS" if not world_readable else "WARN",
        "path": str(path.resolve()),
        "mode_octal": oct(mode),
        "group_readable": group_readable,
        "world_readable": world_readable,
        "note": (
            "Windows ACLs are not fully represented by POSIX mode bits. "
            "Use Windows file security settings for production review."
        ),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V34.0 Broker Credential Vault Foundation"
    )
    p.add_argument(
        "--action",
        choices=["status", "template", "scan", "permissions"],
        default="status",
    )
    p.add_argument(
        "--broker",
        choices=[item.value for item in BrokerName],
        default=None,
    )
    p.add_argument(
        "--template-output",
        default="config/broker_credential_reference_v34_0.json",
    )
    p.add_argument(
        "--scan-root",
        default=".",
    )
    p.add_argument(
        "--permissions-path",
        default="config/broker_credential_reference_v34_0.json",
    )
    p.add_argument(
        "--output",
        default="release/v34/audit/credential_vault_result_v34_0.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)

    if args.action == "status":
        if args.broker:
            payload: Any = asdict(
                inspect_credentials(BrokerName(args.broker))
            )
        else:
            payload = inspect_all()
        success = True

    elif args.action == "template":
        path = Path(args.template_output)
        generate_template(path)
        payload = {
            "status": "PASS",
            "template_path": str(path.resolve()),
            "enabled": False,
            "contains_secret_values": False,
        }
        success = True

    elif args.action == "scan":
        payload = scan_for_plaintext_secrets(Path(args.scan_root).resolve())
        success = payload["status"] == "PASS"

    else:
        payload = check_file_permissions(Path(args.permissions_path))
        success = payload["status"] in {"PASS", "WARN"}

    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
