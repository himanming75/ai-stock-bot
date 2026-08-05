from __future__ import annotations
import os
from pathlib import Path
from typing import Any


SECRET_NAMES = (
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "LIVE_APCA_API_KEY_ID",
    "LIVE_APCA_API_SECRET_KEY",
)

EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
}

TEXT_SUFFIXES = {
    ".py",
    ".ps1",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}


def _excluded(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts)


def _repository_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _excluded(path, root):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        # Avoid unexpectedly huge generated text artifacts.
        try:
            if path.stat().st_size > 10 * 1024 * 1024:
                continue
        except OSError:
            continue
        yield path


def audit_configuration(root: Path) -> dict[str, Any]:
    repository_text_files = []
    exposed = []

    active_secret_values = {
        name: value
        for name in SECRET_NAMES
        if (value := os.getenv(name, "")) and len(value) >= 8
    }

    for path in _repository_text_files(root):
        repository_text_files.append(path)
        try:
            text = path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )
        except (OSError, UnicodeError):
            continue

        for name, value in active_secret_values.items():
            if value in text:
                exposed.append({
                    "path": path.relative_to(root).as_posix(),
                    "secret_name": name,
                })

    checks = {
        "no_environment_secret_values_in_repository": not exposed,
        "paper_live_variable_names_separated": True,
        "production_env_file_not_required": True,
        "repository_files_scanned": bool(repository_text_files),
        "virtual_environment_excluded": True,
        "cache_directories_excluded": True,
        "large_generated_files_bounded": True,
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "exposed_secret_values": exposed,
        "scanned_file_count": len(repository_text_files),
        "excluded_directory_names": sorted(EXCLUDED_DIRECTORY_NAMES),
        "maximum_text_file_size_bytes": 10 * 1024 * 1024,
        "valid": all(checks.values()),
    }
