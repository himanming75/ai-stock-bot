#!/usr/bin/env python3
"""
V29.6 Final Release Builder

Creates and verifies:
- release/manifest/release_manifest.json
- release/manifest/sha256_manifest.json
- release/reports/RELEASE_NOTES.md
- release/certificates/FINAL_RELEASE_CERTIFICATE.json
- dist/ai-stock-trading-bot-v29.6-release.zip

Safety:
- Does not delete project source files.
- Rewrites only known generated release files.
- Excludes .git, virtual environments, caches, and prior release ZIPs.
- Uses Git-tracked files by default when Git is available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

VERSION = "29.6"
SCHEMA_VERSION = "v29.6.release.1"

GENERATED_RELATIVE_PATHS = (
    Path("release/manifest/release_manifest.json"),
    Path("release/manifest/sha256_manifest.json"),
    Path("release/reports/RELEASE_NOTES.md"),
    Path("release/certificates/FINAL_RELEASE_CERTIFICATE.json"),
)

EXCLUDED_PARTS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".idea", ".vscode", "node_modules",
}

EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_commit(root: Path) -> str:
    return run_git(root, "rev-parse", "HEAD") or "UNKNOWN"


def git_branch(root: Path) -> str:
    return run_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "UNKNOWN"


def git_is_clean(root: Path) -> bool | None:
    output = run_git(root, "status", "--porcelain")
    if output is None:
        return None
    return output == ""


def should_include(relative: Path) -> bool:
    if not relative.parts:
        return False
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if relative.name.endswith(".zip"):
        return False
    if relative == Path("release/manifest/sha256_manifest.json"):
        return False
    if relative == Path("release/certificates/FINAL_RELEASE_CERTIFICATE.json"):
        return False
    return True


def collect_source_files(root: Path) -> list[Path]:
    tracked = run_git(root, "ls-files", "-z")
    files: list[Path] = []

    if tracked is not None:
        for raw in tracked.split("\0"):
            if not raw:
                continue
            relative = Path(raw)
            full = root / relative
            if full.is_file() and should_include(relative):
                files.append(relative)
    else:
        # Non-Git fallback: scan the project tree while honoring exclusions.
        for full in root.rglob("*"):
            if not full.is_file():
                continue
            relative = full.relative_to(root)
            if should_include(relative):
                files.append(relative)

    # Include generated report files and other untracked release artifacts,
    # but only from known release subdirectories.
    for folder in (
        root / "release" / "artifacts",
        root / "release" / "reports",
        root / "release" / "certificates",
        root / "release" / "manifest",
    ):
        if folder.exists():
            for full in folder.rglob("*"):
                if full.is_file():
                    relative = full.relative_to(root)
                    if should_include(relative) and relative not in files:
                        files.append(relative)

    return sorted(files, key=lambda p: p.as_posix().lower())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_file_records(root: Path, files: Iterable[Path]) -> list[dict[str, Any]]:
    records = []
    for relative in files:
        full = root / relative
        records.append({
            "path": relative.as_posix(),
            "size_bytes": full.stat().st_size,
            "sha256": sha256_file(full),
        })
    return records


def build_release_manifest(root: Path, generated_at: str) -> dict[str, Any]:
    existing_path = root / "release" / "manifest" / "release_manifest.json"
    existing: dict[str, Any] = {}
    if existing_path.exists():
        try:
            loaded = json.loads(existing_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                existing = loaded
        except (json.JSONDecodeError, UnicodeError):
            existing = {}

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "release_name": existing.get(
            "release_name", "AI Stock Trading Bot Final Candidate"
        ),
        "status": "RELEASE_CANDIDATE",
        "generator": "V29.6 Final Release Builder",
        "generated_at": generated_at,
        "git_commit": git_commit(root),
        "git_branch": git_branch(root),
        "git_clean_at_build_start": git_is_clean(root),
        "audit": existing.get("audit", "PASS"),
        "paper_trading": bool(existing.get("paper_trading", True)),
        "artifact_version": int(existing.get("artifact_version", 1)),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
    }
    return manifest


def build_release_notes(manifest: dict[str, Any], file_count: int) -> str:
    return f"""# AI Stock Trading Bot V{VERSION} Release Candidate

Generated: {manifest['generated_at']}

## Release identity

- Version: {manifest['version']}
- Status: {manifest['status']}
- Git branch: {manifest['git_branch']}
- Git commit: {manifest['git_commit']}
- Git clean at build start: {manifest['git_clean_at_build_start']}
- Packaged files: {file_count}

## Included milestones

- Offline paper-audit certificate verification
- Benchmark and strategy validation
- Walk-forward validation
- Portfolio analytics
- Final report data generation
- V29.5B self-contained HTML tear sheet
- V29.6 reproducible release packaging

## Safety status

This release remains configured for paper trading. It is not a guarantee of
future performance and should not be enabled for live capital until the V29.7
production-readiness audit and all broker-side safeguards pass.

## Verification

Use the SHA-256 manifest and final release certificate in the package to verify
the integrity of each included file.
"""


def build_zip(root: Path, files: Sequence[Path], zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = zip_path.with_suffix(zip_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()

    with zipfile.ZipFile(
        temp_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative in files:
            full = root / relative
            archive.write(full, arcname=relative.as_posix())

    os.replace(temp_path, zip_path)


def verify_records(root: Path, records: Sequence[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for record in records:
        relative = Path(record["path"])
        full = root / relative
        if not full.is_file():
            errors.append(f"Missing file: {relative.as_posix()}")
            continue
        actual_size = full.stat().st_size
        actual_hash = sha256_file(full)
        if actual_size != record["size_bytes"]:
            errors.append(f"Size mismatch: {relative.as_posix()}")
        if actual_hash != record["sha256"]:
            errors.append(f"SHA-256 mismatch: {relative.as_posix()}")
    return errors


def build_release(root: Path, zip_path: Path) -> dict[str, Any]:
    root = root.resolve()
    generated_at = utc_now()

    for relative in GENERATED_RELATIVE_PATHS:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)

    manifest = build_release_manifest(root, generated_at)
    release_manifest_path = root / "release/manifest/release_manifest.json"
    write_json(release_manifest_path, manifest)

    # Release notes are generated before checksums so they are included.
    initial_files = collect_source_files(root)
    notes_path = root / "release/reports/RELEASE_NOTES.md"
    notes_path.write_text(
        build_release_notes(manifest, len(initial_files)),
        encoding="utf-8",
        newline="\n",
    )

    files_for_hash = collect_source_files(root)
    records = build_file_records(root, files_for_hash)

    sha_manifest = {
        "schema_version": "v29.6.sha256_manifest.1",
        "release_version": VERSION,
        "generated_at": generated_at,
        "algorithm": "SHA-256",
        "file_count": len(records),
        "files": records,
    }
    sha_manifest_path = root / "release/manifest/sha256_manifest.json"
    write_json(sha_manifest_path, sha_manifest)

    verification_errors = verify_records(root, records)
    certificate = {
        "schema_version": "v29.6.final_release_certificate.1",
        "release_version": VERSION,
        "generated_at": generated_at,
        "git_commit": manifest["git_commit"],
        "manifest_sha256": sha256_file(release_manifest_path),
        "sha256_manifest_sha256": sha256_file(sha_manifest_path),
        "verified_file_count": len(records),
        "verification_errors": verification_errors,
        "paper_trading_only": True,
        "status": "PASS" if not verification_errors else "FAIL",
    }
    certificate_path = root / "release/certificates/FINAL_RELEASE_CERTIFICATE.json"
    write_json(certificate_path, certificate)

    package_files = collect_source_files(root)
    # Add checksum manifest and certificate after source collection.
    for relative in (
        Path("release/manifest/sha256_manifest.json"),
        Path("release/certificates/FINAL_RELEASE_CERTIFICATE.json"),
    ):
        if relative not in package_files:
            package_files.append(relative)
    package_files = sorted(set(package_files), key=lambda p: p.as_posix().lower())

    build_zip(root, package_files, zip_path)
    zip_hash = sha256_file(zip_path)

    result = {
        "status": certificate["status"],
        "version": VERSION,
        "generated_at": generated_at,
        "git_commit": manifest["git_commit"],
        "packaged_file_count": len(package_files),
        "zip_path": str(zip_path.resolve()),
        "zip_size_bytes": zip_path.stat().st_size,
        "zip_sha256": zip_hash,
        "verification_errors": verification_errors,
    }
    return result


def verify_release(root: Path, zip_path: Path) -> dict[str, Any]:
    root = root.resolve()
    sha_path = root / "release/manifest/sha256_manifest.json"
    cert_path = root / "release/certificates/FINAL_RELEASE_CERTIFICATE.json"

    errors: list[str] = []
    if not sha_path.is_file():
        errors.append("Missing sha256_manifest.json")
        records = []
    else:
        payload = json.loads(sha_path.read_text(encoding="utf-8-sig"))
        records = payload.get("files", [])
        errors.extend(verify_records(root, records))

    if not cert_path.is_file():
        errors.append("Missing FINAL_RELEASE_CERTIFICATE.json")

    if not zip_path.is_file():
        errors.append(f"Missing ZIP: {zip_path}")
    else:
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                bad_member = archive.testzip()
                if bad_member:
                    errors.append(f"Corrupt ZIP member: {bad_member}")
        except zipfile.BadZipFile:
            errors.append("Invalid release ZIP")

    return {
        "status": "PASS" if not errors else "FAIL",
        "verified_file_count": len(records),
        "zip_sha256": sha256_file(zip_path) if zip_path.is_file() else None,
        "errors": errors,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V29.6 Final Release Builder")
    p.add_argument(
        "--root",
        default=".",
        help="Project root containing the .git and release directories",
    )
    p.add_argument(
        "--output",
        default=f"dist/ai-stock-trading-bot-v{VERSION}-release.zip",
        help="Output ZIP path relative to project root unless absolute",
    )
    p.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing release files and ZIP without rebuilding",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    try:
        result = (
            verify_release(root, output)
            if args.verify_only
            else build_release(root, output)
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
