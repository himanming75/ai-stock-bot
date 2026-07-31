from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from typing import Any

VERSION = "76.2"
SCHEMA = "v76.2.targeted_behavioral_capability_verification.1"

class VerificationError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError("config must be an object")
    validate_config(value)
    return value

def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "TARGETED_BEHAVIORAL_CAPABILITY_VERIFICATION":
        raise VerificationError("verification_scope invalid")
    for key in ("offline_only", "preserve_repository", "require_zero_trading_side_effects"):
        if config.get(key) is not True:
            raise VerificationError(f"{key} must be true")
    for key in ("network_allowed", "broker_connection_allowed",
                "order_submission_allowed", "repository_mutation_allowed",
                "live_approval_allowed"):
        if config.get(key) is not False:
            raise VerificationError(f"{key} must be false")
    if config.get("capability_id") != "FEATURE_PIPELINE":
        raise VerificationError("V76.2 must target FEATURE_PIPELINE")
    commands = config.get("verification_commands")
    if not isinstance(commands, list) or not commands:
        raise VerificationError("verification_commands must be non-empty")
    ids = set()
    for item in commands:
        if not isinstance(item, dict):
            raise VerificationError("command must be an object")
        if not item.get("verification_id") or item["verification_id"] in ids:
            raise VerificationError("verification_id missing or duplicate")
        ids.add(item["verification_id"])
        if not isinstance(item.get("script"), str) or not item["script"]:
            raise VerificationError("script required")
        timeout = item.get("timeout_seconds")
        if not isinstance(timeout, int) or timeout < 1 or timeout > 1800:
            raise VerificationError("timeout_seconds must be 1..1800")

def safety_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "AI_STOCK_BOT_NETWORK_ALLOWED": "0",
        "AI_STOCK_BOT_BROKER_ENABLED": "0",
        "AI_STOCK_BOT_ORDER_SUBMISSION_ALLOWED": "0",
        "AI_STOCK_BOT_LIVE_TRADING_ALLOWED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return env

def bounded(text: str, limit: int = 200000) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[-limit:], True

def run_verification(repository_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    if not repository_root.is_dir():
        raise VerificationError(f"repository root not found: {repository_root}")

    records = []
    started = time.time()
    for spec in config["verification_commands"]:
        relative = Path(spec["script"])
        if relative.is_absolute() or ".." in relative.parts:
            raise VerificationError(f"unsafe script path: {relative}")
        script = (repository_root / relative).resolve()
        try:
            script.relative_to(repository_root)
        except ValueError as exc:
            raise VerificationError(f"script outside repository: {script}") from exc

        record: dict[str, Any] = {
            "verification_id": spec["verification_id"],
            "script": relative.as_posix(),
            "required": bool(spec.get("required", True)),
            "exists": script.is_file(),
            "status": "NOT_RUN",
            "return_code": None,
            "timed_out": False,
            "duration_seconds": 0.0,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "script_sha256": file_sha256(script) if script.is_file() else None,
        }
        if not script.is_file():
            record["status"] = "MISSING"
            records.append(record)
            continue

        command = [sys.executable, str(script)]
        command.extend(str(value) for value in spec.get("arguments", []))
        item_start = time.time()
        try:
            completed = subprocess.run(
                command,
                cwd=repository_root,
                env=safety_environment(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=spec["timeout_seconds"],
                shell=False,
            )
            out, out_cut = bounded(completed.stdout)
            err, err_cut = bounded(completed.stderr)
            record.update({
                "status": "PASS" if completed.returncode == 0 else "FAIL",
                "return_code": completed.returncode,
                "stdout": out,
                "stderr": err,
                "stdout_truncated": out_cut,
                "stderr_truncated": err_cut,
            })
        except subprocess.TimeoutExpired as exc:
            out, out_cut = bounded(
                exc.stdout.decode("utf-8", "replace")
                if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            )
            err, err_cut = bounded(
                exc.stderr.decode("utf-8", "replace")
                if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            )
            record.update({
                "status": "TIMEOUT",
                "timed_out": True,
                "stdout": out,
                "stderr": err,
                "stdout_truncated": out_cut,
                "stderr_truncated": err_cut,
            })
        record["duration_seconds"] = round(time.time() - item_start, 6)
        record["record_sha256"] = digest({
            key: value for key, value in record.items() if key != "record_sha256"
        })
        records.append(record)

    required = [x for x in records if x["required"]]
    passed = sum(x["status"] == "PASS" for x in required)
    failed = sum(x["status"] in {"FAIL", "TIMEOUT"} for x in required)
    missing = sum(x["status"] == "MISSING" for x in required)
    overall = "PASS" if required and passed == len(required) else "FAIL"
    capability_state = "BEHAVIOR_VERIFIED" if overall == "PASS" else "BEHAVIOR_GAPS_REMAIN"

    result = {
        "status": overall,
        "decision": (
            "targeted_behavioral_capability_verification_completed"
            if overall == "PASS"
            else "targeted_behavioral_capability_verification_failed"
        ),
        "capability_id": config["capability_id"],
        "capability_state": capability_state,
        "verification_method": "LOCAL_SUBPROCESS_TEST_EXECUTION",
        "verification_count": len(records),
        "required_verification_count": len(required),
        "passed_count": passed,
        "failed_count": failed,
        "missing_count": missing,
        "records": records,
        "records_sha256": digest(records),
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_3_MULTI_CAPABILITY_BEHAVIORAL_VERIFICATION"
            if overall == "PASS"
            else "REPAIR_FEATURE_PIPELINE_BEHAVIOR"
        ),
        "orders_submitted": 0,
        "cash_mutations": 0,
        "position_mutations": 0,
        "portfolio_mutations": 0,
        "repository_mutations_by_verifier": 0,
        "network_allowed": False,
        "broker_connected": False,
        "approved_for_live": False,
        "schema_version": SCHEMA,
        "version": VERSION,
    }
    result["verification_sha256"] = digest(result)
    return result

def write_result(result: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "targeted_behavioral_capability_verification_v76_2.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        config = load_config(Path(args.config))
        result = run_verification(Path(args.repository_root), config)
        output = write_result(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "capability_id": result["capability_id"],
            "capability_state": result["capability_state"],
            "verification_count": result["verification_count"],
            "passed_count": result["passed_count"],
            "failed_count": result["failed_count"],
            "missing_count": result["missing_count"],
            "next_phase": result["next_phase"],
            "orders_submitted": result["orders_submitted"],
            "network_allowed": result["network_allowed"],
            "approved_for_live": result["approved_for_live"],
            "output": str(output),
            "verification_sha256": result["verification_sha256"],
        }, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    except (VerificationError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "targeted_behavioral_capability_verification_failed",
            "error": str(exc),
            "orders_submitted": 0,
            "network_allowed": False,
            "broker_connected": False,
            "approved_for_live": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
