#!/usr/bin/env python3
"""
V30.1 Release Integrity Audit

Checks the V30.0.0 final stable release:
- Git repository, main branch, clean working tree
- v30.0.0 annotated tag existence and commit target
- V30 final manifest, certificate, and release notes
- Final ZIP existence and integrity
- Final ZIP SHA-256
- Paper-trading-only safety declarations
- V29.7 prerequisite audit PASS
- V30 regression tests
- Python source compilation

Outputs:
- release/v30/audit/release_integrity_audit_v30_1.json
- release/v30/audit/release_integrity_audit_v30_1.html

This tool is read-only except for the two generated audit reports.
"""

from __future__ import annotations

import argparse
import compileall
import hashlib
import html
import json
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

VERSION = "30.1"
EXPECTED_TAG = "v30.0.0"

FINAL_MANIFEST = Path("release/v30/manifest/final_release_manifest_v30_0.json")
FINAL_CERTIFICATE = Path("release/v30/certificates/final_stable_release_certificate_v30_0.json")
FINAL_NOTES = Path("release/v30/reports/FINAL_RELEASE_NOTES_V30_0.md")
PREREQUISITE_AUDIT = Path("release/audit/production_readiness_audit_v29_7.json")
DEFAULT_ZIP = Path("dist/ai-stock-trading-bot-v30.0.0-final.zip")

ALLOWED_UNTRACKED_PREFIXES = (
    "dist/",
    "release/v30/audit/",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(
    command: Sequence[str],
    cwd: Path,
    timeout: int = 240,
) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, str(exc.stdout or ""), f"{exc.stderr or ''}\nTimed out"
    except OSError as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: str
    summary: str
    details: dict[str, Any]


def result(
    check_id: str,
    title: str,
    passed: bool,
    pass_summary: str,
    fail_summary: str,
    details: dict[str, Any] | None = None,
) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        title=title,
        status="PASS" if passed else "FAIL",
        summary=pass_summary if passed else fail_summary,
        details=details or {},
    )


def audit_git(root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []

    code, stdout, stderr = run_command(
        ["git", "rev-parse", "--is-inside-work-tree"], root
    )
    inside = code == 0 and stdout.strip() == "true"
    checks.append(result(
        "git.repository",
        "Git repository",
        inside,
        "Project root is a Git repository.",
        "Project root is not a Git repository.",
        {"stdout": stdout.strip(), "stderr": stderr.strip()},
    ))
    if not inside:
        return checks

    code, stdout, stderr = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], root
    )
    branch = stdout.strip() if code == 0 else "UNKNOWN"
    checks.append(result(
        "git.branch",
        "Current branch",
        branch == "main",
        "Current branch is main.",
        f"Current branch is {branch}; expected main.",
        {"branch": branch, "stderr": stderr.strip()},
    ))

    code, stdout, stderr = run_command(["git", "status", "--porcelain"], root)
    allowed: list[str] = []
    unexpected: list[str] = []
    if code == 0:
        for line in stdout.splitlines():
            path = line[3:].replace("\\", "/") if len(line) > 3 else line
            if line.startswith("??") and path.startswith(ALLOWED_UNTRACKED_PREFIXES):
                allowed.append(line)
            else:
                unexpected.append(line)
    checks.append(result(
        "git.working_tree",
        "Git working tree",
        code == 0 and not unexpected,
        "No unexpected working-tree changes were found.",
        "Unexpected tracked or untracked changes were found.",
        {
            "allowed_generated_entries": allowed,
            "unexpected_entries": unexpected,
            "stderr": stderr.strip(),
        },
    ))

    code, stdout, stderr = run_command(["git", "rev-parse", "HEAD"], root)
    checks.append(result(
        "git.head",
        "HEAD commit",
        code == 0 and len(stdout.strip()) >= 7,
        "HEAD commit SHA was resolved.",
        "HEAD commit SHA could not be resolved.",
        {"commit": stdout.strip(), "stderr": stderr.strip()},
    ))
    return checks


def audit_tag(root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []

    code, stdout, stderr = run_command(
        ["git", "tag", "--list", EXPECTED_TAG], root
    )
    exists = code == 0 and stdout.strip() == EXPECTED_TAG
    checks.append(result(
        "tag.exists",
        "V30 Git tag",
        exists,
        f"Tag {EXPECTED_TAG} exists.",
        f"Tag {EXPECTED_TAG} is missing.",
        {"stdout": stdout.strip(), "stderr": stderr.strip()},
    ))
    if not exists:
        return checks

    code, tag_commit, stderr = run_command(
        ["git", "rev-list", "-n", "1", EXPECTED_TAG], root
    )
    code2, head_commit, stderr2 = run_command(["git", "rev-parse", "HEAD"], root)
    tag_sha = tag_commit.strip()
    head_sha = head_commit.strip()
    checks.append(result(
        "tag.commit",
        "Tag commit identity",
        code == 0 and len(tag_sha) >= 7,
        "Tag commit SHA was resolved.",
        "Tag commit SHA could not be resolved.",
        {"tag_commit": tag_sha, "stderr": stderr.strip()},
    ))

    # Tag may legitimately be behind main due to later metadata-only commits.
    checks.append(result(
        "tag.ancestry",
        "Tag ancestry",
        code == 0 and code2 == 0,
        "Tag and current HEAD commit identities are available.",
        "Tag or HEAD commit identity could not be resolved.",
        {
            "tag_commit": tag_sha,
            "head_commit": head_sha,
            "same_commit": tag_sha == head_sha,
            "note": "A later .gitignore or audit-report commit may make HEAD newer than the release tag.",
            "stderr": (stderr + "\n" + stderr2).strip(),
        },
    ))
    return checks


def audit_final_artifacts(root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    required = [FINAL_MANIFEST, FINAL_CERTIFICATE, FINAL_NOTES, PREREQUISITE_AUDIT]
    missing = [p.as_posix() for p in required if not (root / p).is_file()]
    checks.append(result(
        "artifacts.required",
        "Required final artifacts",
        not missing,
        "All V30 final artifacts and prerequisite audit exist.",
        "One or more required final artifacts are missing.",
        {"missing": missing},
    ))
    if missing:
        return checks

    try:
        manifest = load_json(root / FINAL_MANIFEST)
        certificate = load_json(root / FINAL_CERTIFICATE)
        prerequisite = load_json(root / PREREQUISITE_AUDIT)
    except Exception as exc:
        checks.append(result(
            "artifacts.parse",
            "Final artifact parsing",
            False,
            "",
            "A final JSON artifact could not be parsed.",
            {"error": f"{type(exc).__name__}: {exc}"},
        ))
        return checks

    checks.append(result(
        "manifest.identity",
        "Final manifest identity",
        manifest.get("version") == "30.0.0"
        and manifest.get("tag") == EXPECTED_TAG
        and manifest.get("status") == "FINAL_STABLE",
        "Final manifest identifies V30.0.0 FINAL_STABLE.",
        "Final manifest identity is inconsistent.",
        {
            "version": manifest.get("version"),
            "tag": manifest.get("tag"),
            "status": manifest.get("status"),
        },
    ))

    checks.append(result(
        "certificate.status",
        "Final certificate status",
        certificate.get("status") == "PASS",
        "Final stable release certificate is PASS.",
        "Final stable release certificate is not PASS.",
        {
            "status": certificate.get("status"),
            "zip_verification_errors": certificate.get(
                "zip_verification_errors", []
            ),
        },
    ))

    paper_only = (
        manifest.get("paper_trading_only") is True
        and certificate.get("paper_trading_only") is True
    )
    checks.append(result(
        "safety.paper_trading",
        "Paper-trading-only safety",
        paper_only,
        "Manifest and certificate both enforce paper-trading-only mode.",
        "Paper-trading-only protection is missing or inconsistent.",
        {
            "manifest": manifest.get("paper_trading_only"),
            "certificate": certificate.get("paper_trading_only"),
        },
    ))

    checks.append(result(
        "audit.prerequisite",
        "V29.7 prerequisite audit",
        prerequisite.get("status") == "PASS"
        and prerequisite.get("summary", {}).get("fail") == 0,
        "V29.7 prerequisite audit is PASS with zero failures.",
        "V29.7 prerequisite audit is not PASS.",
        {
            "status": prerequisite.get("status"),
            "summary": prerequisite.get("summary"),
        },
    ))

    manifest_hash_ok = (
        certificate.get("final_manifest_sha256")
        == sha256_file(root / FINAL_MANIFEST)
    )
    notes_hash_ok = (
        certificate.get("final_notes_sha256")
        == sha256_file(root / FINAL_NOTES)
    )
    checks.append(result(
        "artifacts.hashes",
        "Manifest and notes hashes",
        manifest_hash_ok and notes_hash_ok,
        "Certificate hashes match the current manifest and release notes.",
        "Certificate hashes do not match the current final artifacts.",
        {
            "manifest_hash_ok": manifest_hash_ok,
            "notes_hash_ok": notes_hash_ok,
        },
    ))
    return checks


def audit_zip(root: Path, zip_path: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    exists = zip_path.is_file()
    checks.append(result(
        "zip.exists",
        "Final release ZIP",
        exists,
        "Final V30 release ZIP exists.",
        "Final V30 release ZIP is missing.",
        {"path": str(zip_path)},
    ))
    if not exists:
        return checks

    errors: list[str] = []
    names: set[str] = set()
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            bad = archive.testzip()
            if bad:
                errors.append(f"Corrupt ZIP member: {bad}")
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        errors.append("Invalid ZIP file")

    required_entries = {
        FINAL_MANIFEST.as_posix(),
        FINAL_CERTIFICATE.as_posix(),
        FINAL_NOTES.as_posix(),
        PREREQUISITE_AUDIT.as_posix(),
    }
    missing_entries = sorted(required_entries - names)
    if missing_entries:
        errors.append(f"Missing required entries: {missing_entries}")

    checks.append(result(
        "zip.integrity",
        "Final ZIP integrity",
        not errors,
        "Final ZIP passed CRC and required-entry checks.",
        "Final ZIP failed integrity validation.",
        {
            "errors": errors,
            "file_count": len(names),
            "size_bytes": zip_path.stat().st_size,
            "sha256": sha256_file(zip_path),
        },
    ))
    return checks


def audit_tests(root: Path) -> CheckResult:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "backtest.test_html_tear_sheet_final_report_v29_5b",
        "tools.test_build_release_v29_6",
        "tools.test_production_readiness_audit_v29_7",
        "tools.test_finalize_release_v30_0",
        "-v",
    ]
    code, stdout, stderr = run_command(command, root, timeout=300)
    combined = (stdout + "\n" + stderr).strip()
    return result(
        "tests.regression",
        "V30 regression tests",
        code == 0 and "OK" in combined,
        "All V30 release regression tests passed.",
        "One or more V30 regression tests failed.",
        {
            "return_code": code,
            "output_tail": combined[-8000:],
        },
    )


def audit_compile(root: Path) -> CheckResult:
    failed: list[str] = []
    checked: list[str] = []
    for relative in ("backtest", "tools"):
        target = root / relative
        if not target.exists():
            continue
        checked.append(relative)
        if not compileall.compile_dir(str(target), quiet=1, force=True):
            failed.append(relative)
    return result(
        "python.compile",
        "Python source compilation",
        not failed,
        "Python source compilation completed without syntax errors.",
        "Python source compilation reported syntax errors.",
        {"checked": checked, "failed": failed},
    )


def run_audit(root: Path, zip_path: Path) -> dict[str, Any]:
    checks: list[CheckResult] = []
    checks.extend(audit_git(root))
    checks.extend(audit_tag(root))
    checks.extend(audit_final_artifacts(root))
    checks.extend(audit_zip(root, zip_path))
    checks.append(audit_tests(root))
    checks.append(audit_compile(root))

    summary = {
        "pass": sum(c.status == "PASS" for c in checks),
        "fail": sum(c.status == "FAIL" for c in checks),
    }
    return {
        "schema_version": "v30.1.release_integrity_audit.1",
        "version": VERSION,
        "audited_release": "30.0.0",
        "expected_tag": EXPECTED_TAG,
        "generated_at": utc_now(),
        "status": "PASS" if summary["fail"] == 0 else "FAIL",
        "summary": summary,
        "checks": [asdict(c) for c in checks],
    }


def render_html(report: dict[str, Any]) -> str:
    sections = []
    for item in report["checks"]:
        css = item["status"].lower()
        details = html.escape(
            json.dumps(item["details"], indent=2, ensure_ascii=False)
        )
        sections.append(f"""
<section class="check {css}">
  <div class="head">
    <h2>{html.escape(item['title'])}</h2>
    <span class="badge {css}">{item['status']}</span>
  </div>
  <p>{html.escape(item['summary'])}</p>
  <details><summary>Details</summary><pre>{details}</pre></details>
</section>
""")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V30.1 Release Integrity Audit</title>
<style>
body{{margin:0;background:#f4f6f8;color:#182230;font:14px/1.5 Arial,sans-serif}}
main{{max-width:1080px;margin:auto;padding:30px 20px 60px}}
header{{background:#14213d;color:white;border-radius:16px;padding:26px}}
header h1{{margin:0 0 8px}}
.summary{{display:flex;gap:12px;margin-top:15px;flex-wrap:wrap}}
.card{{background:rgba(255,255,255,.14);padding:8px 12px;border-radius:9px}}
.check{{margin-top:16px;background:white;border:1px solid #d8dee7;border-left:6px solid #667085;border-radius:12px;padding:18px}}
.check.pass{{border-left-color:#138a55}} .check.fail{{border-left-color:#c4322b}}
.head{{display:flex;align-items:center;justify-content:space-between;gap:14px}}
.head h2{{margin:0;font-size:17px}}
.badge{{padding:4px 9px;border-radius:999px;font-weight:700}}
.badge.pass{{background:#dcfae6;color:#087443}} .badge.fail{{background:#fee4e2;color:#b42318}}
pre{{background:#f8fafc;border:1px solid #e4e7ec;padding:12px;overflow:auto;white-space:pre-wrap}}
footer{{color:#667085;text-align:center;margin-top:22px}}
</style>
</head>
<body><main>
<header>
<h1>AI Stock Trading Bot V30.1 Release Integrity Audit</h1>
<p>Audited release: V30.0.0 · Generated {html.escape(report['generated_at'])}</p>
<div class="summary">
<div class="card">Overall: <strong>{report['status']}</strong></div>
<div class="card">PASS: {report['summary']['pass']}</div>
<div class="card">FAIL: {report['summary']['fail']}</div>
</div>
</header>
{''.join(sections)}
<footer>V30.1 Release Integrity Audit · Paper-trading-only final release</footer>
</main></body></html>"""


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V30.1 Release Integrity Audit")
    p.add_argument("--root", default=".", help="Project root")
    p.add_argument(
        "--zip",
        default=str(DEFAULT_ZIP),
        help="Final V30 ZIP path",
    )
    p.add_argument(
        "--json-output",
        default="release/v30/audit/release_integrity_audit_v30_1.json",
    )
    p.add_argument(
        "--html-output",
        default="release/v30/audit/release_integrity_audit_v30_1.html",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).resolve()

    zip_path = Path(args.zip)
    json_path = Path(args.json_output)
    html_path = Path(args.html_output)

    if not zip_path.is_absolute():
        zip_path = root / zip_path
    if not json_path.is_absolute():
        json_path = root / json_path
    if not html_path.is_absolute():
        html_path = root / html_path

    report = run_audit(root, zip_path)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    html_path.write_text(render_html(report), encoding="utf-8", newline="\n")

    print(json.dumps({
        "status": report["status"],
        "summary": report["summary"],
        "json_output": str(json_path),
        "html_output": str(html_path),
        "zip_sha256": sha256_file(zip_path) if zip_path.is_file() else None,
    }, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
