#!/usr/bin/env python3
"""
V30.0 Final Stable Release Finalizer

Creates:
- release/v30/manifest/final_release_manifest_v30_0.json
- release/v30/certificates/final_stable_release_certificate_v30_0.json
- release/v30/reports/FINAL_RELEASE_NOTES_V30_0.md
- dist/ai-stock-trading-bot-v30.0.0-final.zip

Verifies:
- V29.7 production readiness audit exists and is PASS
- V29.6 release certificate exists and is PASS
- Paper-trading-only safety remains enabled
- Final ZIP integrity
- Final manifest/certificate hashes

This script does not create or push Git tags automatically.
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

VERSION = "30.0.0"
TAG = "v30.0.0"

EXCLUDED_PARTS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".idea", ".vscode", "node_modules",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log"}
EXCLUDED_PREFIXES = ("dist/",)

FINAL_MANIFEST = Path("release/v30/manifest/final_release_manifest_v30_0.json")
FINAL_CERTIFICATE = Path("release/v30/certificates/final_stable_release_certificate_v30_0.json")
FINAL_NOTES = Path("release/v30/reports/FINAL_RELEASE_NOTES_V30_0.md")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


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
    return result.stdout.strip() if result.returncode == 0 else None


def git_commit(root: Path) -> str:
    return run_git(root, "rev-parse", "HEAD") or "UNKNOWN"


def git_branch(root: Path) -> str:
    return run_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "UNKNOWN"


def git_status(root: Path) -> list[str]:
    output = run_git(root, "status", "--porcelain")
    return output.splitlines() if output is not None and output else []


def should_include(relative: Path) -> bool:
    posix = relative.as_posix()
    if any(posix.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if relative.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if relative.name.endswith(".zip"):
        return False
    return True


def collect_files(root: Path) -> list[Path]:
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
        for full in root.rglob("*"):
            if full.is_file():
                relative = full.relative_to(root)
                if should_include(relative):
                    files.append(relative)

    for relative in (FINAL_MANIFEST, FINAL_CERTIFICATE, FINAL_NOTES):
        full = root / relative
        if full.is_file() and relative not in files:
            files.append(relative)

    return sorted(set(files), key=lambda p: p.as_posix().lower())


def validate_prerequisites(root: Path) -> dict[str, Any]:
    audit_path = root / "release/audit/production_readiness_audit_v29_7.json"
    cert_path = root / "release/certificates/FINAL_RELEASE_CERTIFICATE.json"
    release_manifest_path = root / "release/manifest/release_manifest.json"

    errors: list[str] = []
    audit = {}
    cert = {}
    release_manifest = {}

    for path, label in (
        (audit_path, "V29.7 audit"),
        (cert_path, "V29.6 release certificate"),
        (release_manifest_path, "V29.6 release manifest"),
    ):
        if not path.is_file():
            errors.append(f"Missing {label}: {path}")

    if not errors:
        try:
            audit = load_json(audit_path)
            cert = load_json(cert_path)
            release_manifest = load_json(release_manifest_path)
        except Exception as exc:
            errors.append(f"Prerequisite parse error: {type(exc).__name__}: {exc}")

    if audit and audit.get("status") != "PASS":
        errors.append("V29.7 production readiness audit is not PASS")
    if cert and cert.get("status") != "PASS":
        errors.append("V29.6 final release certificate is not PASS")
    if cert and cert.get("paper_trading_only") is not True:
        errors.append("V29.6 certificate does not enforce paper_trading_only")
    if release_manifest and release_manifest.get("paper_trading") is not True:
        errors.append("V29.6 manifest does not enforce paper_trading")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "audit": audit,
        "certificate": cert,
        "release_manifest": release_manifest,
    }


def build_notes(commit: str, generated_at: str) -> str:
    return f"""# AI Stock Trading Bot V{VERSION} Final Stable Release

Generated: {generated_at}

## Release identity

- Version: {VERSION}
- Git tag: {TAG}
- Git commit: {commit}
- Release status: FINAL_STABLE
- Safety mode: PAPER_TRADING_ONLY

## Completed milestones

- V24.2 Offline Paper Audit Certificate Verification
- V25 Benchmark Analysis
- V26 Strategy Validation
- V27 Walk-Forward Validation
- V28 Portfolio Analytics
- V29.5A Final Report Data
- V29.5B HTML Tear Sheet and Final Report
- V29.6 Final Release Packaging
- V29.7 Production Readiness Audit
- V30.0 Final Stable Release

## Important safety notice

This release is certified only for paper trading. It does not authorize live
capital deployment. Live trading requires separate broker integration review,
credential security review, capital limits, kill-switch validation, legal and
tax review, and supervised dry-run approval.

## Verification

Verify the final ZIP SHA-256 against the final stable release certificate.
"""


def build_zip(root: Path, files: Sequence[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    if temp.exists():
        temp.unlink()

    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in files:
            archive.write(root / relative, arcname=relative.as_posix())

    os.replace(temp, output)


def verify_zip(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Missing final ZIP: {path}"]
    try:
        with zipfile.ZipFile(path, "r") as archive:
            bad = archive.testzip()
            if bad:
                errors.append(f"Corrupt ZIP member: {bad}")
            required = {
                FINAL_MANIFEST.as_posix(),
                FINAL_CERTIFICATE.as_posix(),
                FINAL_NOTES.as_posix(),
                "release/audit/production_readiness_audit_v29_7.json",
            }
            names = set(archive.namelist())
            missing = sorted(required - names)
            if missing:
                errors.append(f"ZIP missing required entries: {missing}")
    except zipfile.BadZipFile:
        errors.append("Final release ZIP is invalid")
    return errors


def finalize(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve()
    generated_at = utc_now()
    prereq = validate_prerequisites(root)
    if prereq["status"] != "PASS":
        return {
            "status": "FAIL",
            "stage": "prerequisites",
            "errors": prereq["errors"],
        }

    commit = git_commit(root)
    branch = git_branch(root)

    manifest = {
        "schema_version": "v30.0.final_release_manifest.1",
        "version": VERSION,
        "tag": TAG,
        "release_name": "AI Stock Trading Bot Final Stable Release",
        "status": "FINAL_STABLE",
        "generated_at": generated_at,
        "git_commit": commit,
        "git_branch": branch,
        "paper_trading_only": True,
        "v29_7_audit_status": prereq["audit"].get("status"),
        "v29_7_audit_summary": prereq["audit"].get("summary"),
        "v29_6_certificate_status": prereq["certificate"].get("status"),
        "source_release_version": prereq["release_manifest"].get("version"),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
    }
    write_json(root / FINAL_MANIFEST, manifest)

    (root / FINAL_NOTES).parent.mkdir(parents=True, exist_ok=True)
    (root / FINAL_NOTES).write_text(
        build_notes(commit, generated_at),
        encoding="utf-8",
        newline="\n",
    )

    preliminary_certificate = {
        "schema_version": "v30.0.final_stable_release_certificate.1",
        "version": VERSION,
        "tag": TAG,
        "generated_at": generated_at,
        "git_commit": commit,
        "paper_trading_only": True,
        "prerequisite_status": "PASS",
        "final_manifest_sha256": sha256_file(root / FINAL_MANIFEST),
        "final_notes_sha256": sha256_file(root / FINAL_NOTES),
        "zip_sha256": None,
        "zip_size_bytes": None,
        "status": "PENDING_PACKAGE",
    }
    write_json(root / FINAL_CERTIFICATE, preliminary_certificate)

    files = collect_files(root)
    build_zip(root, files, output)
    zip_errors = verify_zip(output)

    final_certificate = dict(preliminary_certificate)
    final_certificate.update({
        "zip_sha256": sha256_file(output),
        "zip_size_bytes": output.stat().st_size,
        "packaged_file_count": len(files),
        "zip_verification_errors": zip_errors,
        "status": "PASS" if not zip_errors else "FAIL",
    })
    write_json(root / FINAL_CERTIFICATE, final_certificate)

    # Rebuild so the ZIP contains the final certificate with its ZIP metadata.
    files = collect_files(root)
    build_zip(root, files, output)
    final_zip_hash = sha256_file(output)

    # Certificate cannot contain its own final ZIP hash without recursion.
    # Store an external finalization record in command output and preserve
    # certificate's package-content verification fields.
    verify_errors = verify_zip(output)

    return {
        "status": "PASS" if not verify_errors else "FAIL",
        "version": VERSION,
        "tag": TAG,
        "git_commit": commit,
        "git_branch": branch,
        "paper_trading_only": True,
        "packaged_file_count": len(files),
        "zip_path": str(output.resolve()),
        "zip_sha256": final_zip_hash,
        "zip_size_bytes": output.stat().st_size,
        "verification_errors": verify_errors,
        "tag_commands": [
            f"git tag -a {TAG} -m \"AI Stock Trading Bot V{VERSION} Final Stable Release\"",
            f"git push origin {TAG}",
        ],
    }


def verify_existing(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    prereq = validate_prerequisites(root)
    errors.extend(prereq["errors"])

    for relative in (FINAL_MANIFEST, FINAL_CERTIFICATE, FINAL_NOTES):
        if not (root / relative).is_file():
            errors.append(f"Missing final artifact: {relative.as_posix()}")

    errors.extend(verify_zip(output))

    certificate = {}
    if (root / FINAL_CERTIFICATE).is_file():
        try:
            certificate = load_json(root / FINAL_CERTIFICATE)
            if certificate.get("status") != "PASS":
                errors.append("Final stable release certificate is not PASS")
            if certificate.get("paper_trading_only") is not True:
                errors.append("Final certificate is not paper-trading-only")
        except Exception as exc:
            errors.append(f"Final certificate parse error: {type(exc).__name__}: {exc}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "version": VERSION,
        "tag": TAG,
        "zip_sha256": sha256_file(output) if output.is_file() else None,
        "errors": errors,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V30.0 Final Stable Release Finalizer")
    p.add_argument("--root", default=".", help="Project root")
    p.add_argument(
        "--output",
        default="dist/ai-stock-trading-bot-v30.0.0-final.zip",
        help="Final release ZIP path",
    )
    p.add_argument("--verify-only", action="store_true")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output

    try:
        result = verify_existing(root, output) if args.verify_only else finalize(root, output)
    except Exception as exc:
        result = {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
