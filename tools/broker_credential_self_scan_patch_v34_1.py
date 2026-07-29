#!/usr/bin/env python3
"""
V34.1 Broker Credential Vault - Self-Scan Exclusion Patch

Changes from V34.0:
- Excludes test files and generated artifacts from plaintext-secret scans
- Excludes release/, dist/, .git/, virtual environments, caches, and IDE files
- Excludes the scanner's own test fixtures
- Keeps suspicious real files such as .env detectable
- Adds explicit scan policy reporting

No network requests and no broker authentication are performed.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


VERSION = "34.1"

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "dist",
    "release",
    "node_modules",
}

EXCLUDED_FILE_PATTERNS = (
    "test_*.py",
    "*_test.py",
    "*.pyc",
    "*.pyo",
    "*.zip",
    "*.log",
)

SUSPICIOUS_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "secrets.json",
    "credentials.json",
    "api_keys.json",
    "broker_credentials.json",
}

SCANNABLE_SUFFIXES = {
    "",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".txt",
    ".md",
    ".ps1",
    ".bat",
    ".cmd",
}

SECRET_PATTERNS = [
    re.compile(
        r"(?i)(api[_-]?key|api[_-]?secret|client[_-]?secret|"
        r"refresh[_-]?token|access[_-]?token)\s*[:=]\s*"
        r"['\"]?([A-Za-z0-9_\-]{12,})"
    ),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def matches_excluded_file(path: Path) -> bool:
    return any(path.match(pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def should_scan(root: Path, path: Path) -> tuple[bool, str | None]:
    relative = path.relative_to(root)

    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts[:-1]):
        return False, "excluded_directory"

    if matches_excluded_file(relative):
        return False, "excluded_file_pattern"

    if (
        path.suffix.lower() not in SCANNABLE_SUFFIXES
        and path.name.lower() not in SUSPICIOUS_FILE_NAMES
    ):
        return False, "unsupported_suffix"

    return True, None


def scan_for_plaintext_secrets(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    scanned = 0
    skipped = 0
    skipped_by_reason: dict[str, int] = {}

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        allowed, reason = should_scan(root, path)
        if not allowed:
            skipped += 1
            key = reason or "unknown"
            skipped_by_reason[key] = skipped_by_reason.get(key, 0) + 1
            continue

        scanned += 1
        relative = path.relative_to(root)
        name_flag = path.name.lower() in SUSPICIOUS_FILE_NAMES
        pattern_hits = 0

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            skipped += 1
            skipped_by_reason["read_error"] = (
                skipped_by_reason.get("read_error", 0) + 1
            )
            continue

        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                pattern_hits += 1

        if name_flag or pattern_hits:
            findings.append(
                {
                    "path": relative.as_posix(),
                    "suspicious_filename": name_flag,
                    "pattern_hit_count": pattern_hits,
                }
            )

    return {
        "schema_version": "v34.1.plaintext_secret_scan.1",
        "version": VERSION,
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
        "scanned_file_count": scanned,
        "skipped_file_count": skipped,
        "skipped_by_reason": skipped_by_reason,
        "excluded_directories": sorted(EXCLUDED_DIRECTORY_NAMES),
        "excluded_file_patterns": list(EXCLUDED_FILE_PATTERNS),
        "raw_secret_values_included": False,
        "generated_at": utc_now(),
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
        description="V34.1 Self-Scan Exclusion Patch"
    )
    p.add_argument("--scan-root", default=".")
    p.add_argument(
        "--output",
        default="release/v34/audit/plaintext_secret_scan_v34_1.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    payload = scan_for_plaintext_secrets(Path(args.scan_root))
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
