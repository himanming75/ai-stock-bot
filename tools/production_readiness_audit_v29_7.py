#!/usr/bin/env python3
"""
V29.7 Production Readiness Audit

Read-only audit of the project with generated reports under release/audit/.

Checks:
- Git repository and branch
- Git working tree cleanliness, with generated dist/ optionally ignored
- Required V29.5B / V29.6 files
- V29.6 release verification
- Release certificate status
- SHA-256 manifest integrity
- HTML generator import/CLI availability
- Targeted V29.5B + V29.6 unit tests
- Python source compilation
- Paper-trading safety declaration

Outputs:
- release/audit/production_readiness_audit_v29_7.json
- release/audit/production_readiness_audit_v29_7.html

No project source files are modified or deleted.
"""

from __future__ import annotations

import argparse
import compileall
import html
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

VERSION = "29.7"

REQUIRED_FILES = [
    "backtest/html_tear_sheet_final_report_v29_5b.py",
    "backtest/test_html_tear_sheet_final_report_v29_5b.py",
    "tools/build_release_v29_6.py",
    "tools/test_build_release_v29_6.py",
    "release/manifest/release_manifest.json",
    "release/manifest/sha256_manifest.json",
    "release/reports/RELEASE_NOTES.md",
    "release/certificates/FINAL_RELEASE_CERTIFICATE.json",
]

ALLOWED_UNTRACKED_PREFIXES = ("dist/", "release/audit/")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(
    command: Sequence[str],
    cwd: Path,
    timeout: int = 180,
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
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        return 124, str(stdout), f"{stderr}\nCommand timed out after {timeout}s"
    except OSError as exc:
        return 127, "", f"{type(exc).__name__}: {exc}"


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: str
    summary: str
    details: dict[str, Any]


def check(
    check_id: str,
    title: str,
    passed: bool,
    summary_pass: str,
    summary_fail: str,
    details: dict[str, Any] | None = None,
    warning: bool = False,
) -> CheckResult:
    status = "WARN" if warning else ("PASS" if passed else "FAIL")
    return CheckResult(
        check_id=check_id,
        title=title,
        status=status,
        summary=summary_pass if passed else summary_fail,
        details=details or {},
    )


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return loaded


def audit_git(root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []

    code, stdout, stderr = run_command(["git", "rev-parse", "--is-inside-work-tree"], root)
    inside = code == 0 and stdout.strip() == "true"
    results.append(check(
        "git.repository",
        "Git repository",
        inside,
        "Project root is a Git working tree.",
        "Project root is not recognized as a Git working tree.",
        {"stdout": stdout.strip(), "stderr": stderr.strip()},
    ))
    if not inside:
        return results

    code, branch, branch_err = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    branch_name = branch.strip() if code == 0 else "UNKNOWN"
    results.append(check(
        "git.branch",
        "Release branch",
        branch_name == "main",
        "Current branch is main.",
        f"Current branch is {branch_name}; expected main.",
        {"branch": branch_name, "stderr": branch_err.strip()},
    ))

    code, commit, commit_err = run_command(["git", "rev-parse", "HEAD"], root)
    results.append(check(
        "git.commit",
        "Git commit identity",
        code == 0 and len(commit.strip()) >= 7,
        "Current commit SHA was resolved.",
        "Current commit SHA could not be resolved.",
        {"commit": commit.strip(), "stderr": commit_err.strip()},
    ))

    code, status_out, status_err = run_command(["git", "status", "--porcelain"], root)
    unexpected = []
    allowed = []
    if code == 0:
        for line in status_out.splitlines():
            path = line[3:].replace("\\", "/") if len(line) >= 4 else line
            if path.startswith(ALLOWED_UNTRACKED_PREFIXES) and line.startswith("??"):
                allowed.append(line)
            else:
                unexpected.append(line)

    results.append(check(
        "git.working_tree",
        "Git working tree",
        code == 0 and not unexpected,
        "No unexpected working-tree changes were found.",
        "Unexpected tracked or untracked changes were found.",
        {
            "allowed_generated_entries": allowed,
            "unexpected_entries": unexpected,
            "stderr": status_err.strip(),
        },
        warning=False,
    ))
    return results


def audit_required_files(root: Path) -> CheckResult:
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    return check(
        "files.required",
        "Required release files",
        not missing,
        "All required V29.5B and V29.6 files exist.",
        "One or more required release files are missing.",
        {"required_count": len(REQUIRED_FILES), "missing": missing},
    )


def audit_release_certificate(root: Path) -> CheckResult:
    path = root / "release/certificates/FINAL_RELEASE_CERTIFICATE.json"
    if not path.is_file():
        return check(
            "release.certificate",
            "Final release certificate",
            False,
            "",
            "Final release certificate is missing.",
            {"path": str(path)},
        )
    try:
        data = load_json(path)
        passed = data.get("status") == "PASS" and data.get("paper_trading_only") is True
        return check(
            "release.certificate",
            "Final release certificate",
            passed,
            "Release certificate is PASS and paper-trading-only.",
            "Release certificate is not PASS or lacks paper-trading-only protection.",
            {
                "status": data.get("status"),
                "paper_trading_only": data.get("paper_trading_only"),
                "verification_errors": data.get("verification_errors", []),
            },
        )
    except Exception as exc:
        return check(
            "release.certificate",
            "Final release certificate",
            False,
            "",
            "Release certificate could not be parsed.",
            {"error": f"{type(exc).__name__}: {exc}"},
        )


def audit_release_builder(root: Path) -> CheckResult:
    builder = root / "tools/build_release_v29_6.py"
    if not builder.is_file():
        return check(
            "release.verify",
            "V29.6 release verification",
            False,
            "",
            "Release Builder is missing.",
            {"path": str(builder)},
        )

    code, stdout, stderr = run_command(
        [sys.executable, str(builder), "--root", str(root), "--verify-only"],
        root,
        timeout=180,
    )
    payload: dict[str, Any] = {}
    parse_error = None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)

    passed = code == 0 and payload.get("status") == "PASS"
    return check(
        "release.verify",
        "V29.6 release verification",
        passed,
        "V29.6 package and SHA-256 records verified successfully.",
        "V29.6 release verification failed.",
        {
            "return_code": code,
            "payload": payload,
            "parse_error": parse_error,
            "stderr": stderr.strip(),
        },
    )


def audit_targeted_tests(root: Path) -> CheckResult:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "backtest.test_html_tear_sheet_final_report_v29_5b",
        "tools.test_build_release_v29_6",
        "-v",
    ]
    code, stdout, stderr = run_command(command, root, timeout=240)
    combined = (stdout + "\n" + stderr).strip()
    passed = code == 0 and "OK" in combined
    return check(
        "tests.targeted",
        "V29.5B and V29.6 regression tests",
        passed,
        "All targeted release regression tests passed.",
        "One or more targeted release regression tests failed.",
        {
            "return_code": code,
            "output_tail": combined[-6000:],
        },
    )


def audit_html_generator(root: Path) -> CheckResult:
    generator = root / "backtest/html_tear_sheet_final_report_v29_5b.py"
    code, stdout, stderr = run_command(
        [sys.executable, str(generator), "--help"],
        root,
        timeout=60,
    )
    passed = code == 0 and "V29.5B" in (stdout + stderr)
    return check(
        "report.generator",
        "HTML Tear Sheet generator",
        passed,
        "V29.5B HTML generator CLI is available.",
        "V29.5B HTML generator CLI check failed.",
        {
            "return_code": code,
            "stdout": stdout[-2000:],
            "stderr": stderr[-2000:],
        },
    )


def audit_python_compile(root: Path) -> CheckResult:
    targets = [root / "backtest", root / "tools"]
    failed = []
    checked = []
    for target in targets:
        if not target.exists():
            continue
        ok = compileall.compile_dir(
            str(target),
            quiet=1,
            force=True,
            legacy=False,
        )
        checked.append(str(target.relative_to(root)))
        if not ok:
            failed.append(str(target.relative_to(root)))

    return check(
        "python.compile",
        "Python source compilation",
        not failed,
        "Python source compilation completed without syntax errors.",
        "Python source compilation reported syntax errors.",
        {"checked": checked, "failed": failed},
    )


def audit_paper_trading(root: Path) -> CheckResult:
    manifest_path = root / "release/manifest/release_manifest.json"
    if not manifest_path.is_file():
        return check(
            "safety.paper_trading",
            "Paper-trading safety mode",
            False,
            "",
            "Release manifest is missing.",
            {},
        )
    try:
        manifest = load_json(manifest_path)
        passed = manifest.get("paper_trading") is True
        return check(
            "safety.paper_trading",
            "Paper-trading safety mode",
            passed,
            "Release manifest explicitly requires paper trading.",
            "Release manifest does not explicitly require paper trading.",
            {"paper_trading": manifest.get("paper_trading")},
        )
    except Exception as exc:
        return check(
            "safety.paper_trading",
            "Paper-trading safety mode",
            False,
            "",
            "Release manifest could not be parsed.",
            {"error": f"{type(exc).__name__}: {exc}"},
        )


def render_html(report: dict[str, Any]) -> str:
    rows = []
    for item in report["checks"]:
        status = item["status"]
        css = status.lower()
        details = html.escape(json.dumps(item["details"], indent=2, ensure_ascii=False))
        rows.append(f"""
        <section class="check {css}">
          <div class="check-head">
            <h2>{html.escape(item["title"])}</h2>
            <span class="badge {css}">{status}</span>
          </div>
          <p>{html.escape(item["summary"])}</p>
          <details><summary>Details</summary><pre>{details}</pre></details>
        </section>
        """)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V{VERSION} Production Readiness Audit</title>
<style>
body{{margin:0;background:#f3f5f8;color:#182230;font:14px/1.5 Arial,sans-serif}}
main{{max-width:1050px;margin:0 auto;padding:30px 20px 60px}}
header{{background:#172554;color:white;padding:26px;border-radius:16px}}
header h1{{margin:0 0 8px}} .summary{{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}}
.card{{background:rgba(255,255,255,.13);padding:8px 12px;border-radius:9px}}
.check{{background:white;border:1px solid #d9e0e8;border-left:6px solid #667085;border-radius:12px;padding:18px;margin-top:16px}}
.check.pass{{border-left-color:#138a55}} .check.fail{{border-left-color:#c4322b}} .check.warn{{border-left-color:#c77700}}
.check-head{{display:flex;justify-content:space-between;gap:15px;align-items:center}}
.check h2{{font-size:17px;margin:0}} .badge{{font-weight:700;border-radius:999px;padding:4px 9px}}
.badge.pass{{background:#dcfae6;color:#087443}} .badge.fail{{background:#fee4e2;color:#b42318}} .badge.warn{{background:#fef0c7;color:#93370d}}
pre{{background:#f8fafc;border:1px solid #e4e7ec;padding:12px;overflow:auto;white-space:pre-wrap}}
footer{{color:#667085;text-align:center;margin-top:20px}}
</style>
</head>
<body><main>
<header>
<h1>AI Stock Trading Bot V{VERSION} Production Readiness Audit</h1>
<p>Generated {html.escape(report['generated_at'])}</p>
<div class="summary">
<div class="card">Overall: <strong>{html.escape(report['status'])}</strong></div>
<div class="card">PASS: {report['summary']['pass']}</div>
<div class="card">WARN: {report['summary']['warn']}</div>
<div class="card">FAIL: {report['summary']['fail']}</div>
</div>
</header>
{''.join(rows)}
<footer>V{VERSION} Production Readiness Audit · Paper-trading release candidate</footer>
</main></body></html>"""


def run_audit(root: Path) -> dict[str, Any]:
    results: list[CheckResult] = []
    results.extend(audit_git(root))
    results.append(audit_required_files(root))
    results.append(audit_release_certificate(root))
    results.append(audit_release_builder(root))
    results.append(audit_html_generator(root))
    results.append(audit_targeted_tests(root))
    results.append(audit_python_compile(root))
    results.append(audit_paper_trading(root))

    counts = {
        "pass": sum(r.status == "PASS" for r in results),
        "warn": sum(r.status == "WARN" for r in results),
        "fail": sum(r.status == "FAIL" for r in results),
    }
    return {
        "schema_version": "v29.7.production_readiness_audit.1",
        "version": VERSION,
        "generated_at": utc_now(),
        "status": "PASS" if counts["fail"] == 0 else "FAIL",
        "summary": counts,
        "checks": [asdict(r) for r in results],
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V29.7 Production Readiness Audit")
    p.add_argument("--root", default=".", help="Project root")
    p.add_argument(
        "--json-output",
        default="release/audit/production_readiness_audit_v29_7.json",
    )
    p.add_argument(
        "--html-output",
        default="release/audit/production_readiness_audit_v29_7.html",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.root).resolve()

    json_path = Path(args.json_output)
    html_path = Path(args.html_output)
    if not json_path.is_absolute():
        json_path = root / json_path
    if not html_path.is_absolute():
        html_path = root / html_path

    report = run_audit(root)
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
    }, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
