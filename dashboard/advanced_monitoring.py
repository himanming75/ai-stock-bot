from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _load_jsonl(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def performance_series(root: Path) -> dict[str, list[dict[str, Any]]]:
    curve = _load_json(
        root / "release/op2_05_to_op2_08/actual/shadow_equity_curve.json"
    )
    points = curve.get("equity_curve", [])
    if not isinstance(points, list):
        points = []
    equity, drawdown = [], []
    for index, item in enumerate(points, start=1):
        if not isinstance(item, dict):
            continue
        trade_number = int(item.get("trade_number", index))
        equity.append({"x": trade_number, "y": _number(item.get("cumulative_pnl", 0))})
        drawdown.append({"x": trade_number, "y": _number(item.get("drawdown", 0))})
    if not equity:
        equity = [{"x": 0, "y": 0.0}]
        drawdown = [{"x": 0, "y": 0.0}]
    return {"equity": equity, "drawdown": drawdown}


def event_log(root: Path, limit: int = 25) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in [
        root / "release/op2_13_to_op2_16/actual/shadow_signal_queue.jsonl",
        root / "release/op2_01_to_op2_04/actual/shadow_decision_ledger.jsonl",
        root / "release/op3_09_to_op3_12/actual/paper_order_lifecycle_audit_ledger.jsonl",
        root / "release/op3_13_to_op3_16/actual/limited_autonomous_runtime_ledger.jsonl",
    ]:
        for item in _load_jsonl(path, limit=limit):
            records.append({
                "timestamp": str(item.get("observed_at", item.get("submitted_at", item.get("created_at", "")))),
                "category": str(item.get("stage", item.get("stage_range", item.get("status", "EVENT")))),
                "message": _event_message(item),
                "severity": "INFO",
            })
    records.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
    return records[:limit]


def alerts(root: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    paper = _load_json(
        root / "release/dash2_05/actual/current_paper_snapshot.json"
    )
    collector = _load_json(
        root / "release/dash2_05/actual/current_paper_snapshot_collector_result.json"
    )
    limited = _load_json(
        root / "release/op3_13_to_op3_16/actual/limited_autonomous_paper_trading_result.json"
    )
    lifecycle = _load_json(
        root / "release/op3_09_to_op3_12/actual/paper_order_lifecycle_result.json"
    )

    if not paper:
        output.append(_alert("CRITICAL", "ACTUAL_PAPER_SNAPSHOT_MISSING", "Run the read-only Paper snapshot collector."))
    elif not _snapshot_fresh(paper, 300):
        output.append(_alert("WARNING", "ACTUAL_PAPER_SNAPSHOT_STALE", "Paper snapshot is older than five minutes."))

    if collector.get("safe_mode_engaged"):
        output.append(_alert("CRITICAL", "PAPER_SNAPSHOT_COLLECTOR_BLOCKED", "The read-only Paper snapshot collector is blocked."))

    if lifecycle.get("recovery_required"):
        output.append(_alert("WARNING", "PAPER_ORDER_RECOVERY_REQUIRED", str(lifecycle.get("order_status", "open"))))

    if limited.get("safe_mode_engaged"):
        for issue in limited.get("issues", []):
            if isinstance(issue, dict):
                output.append(_alert("WARNING", str(issue.get("code", "PAPER_RUNTIME_BLOCKED")), str(issue.get("detail", ""))))

    disk = shutil.disk_usage(root)
    used_pct = ((disk.total - disk.free) / disk.total * 100) if disk.total else 0
    if used_pct >= 95:
        output.append(_alert("CRITICAL", "DISK_USAGE_CRITICAL", f"Disk usage is {used_pct:.2f}%."))

    if not output:
        output.append(_alert("INFO", "PAPER_SYSTEM_HEALTHY", "No active Paper dashboard alerts."))
    return output


def dashboard_health(root: Path) -> dict[str, Any]:
    monitored = [
        root / "release/dash2_05/actual/current_paper_snapshot.json",
        root / "release/op3_09_to_op3_12/actual/paper_order_lifecycle_result.json",
        root / "release/op3_13_to_op3_16/actual/limited_autonomous_paper_trading_result.json",
    ]
    integrity = []
    newest_mtime = 0.0
    for path in monitored:
        valid = bool(_load_json(path)) if path.exists() else False
        mtime = path.stat().st_mtime if path.exists() else 0.0
        newest_mtime = max(newest_mtime, mtime)
        integrity.append({
            "path": str(path.relative_to(root)),
            "exists": path.exists(),
            "valid_json": valid,
        })
    usage = shutil.disk_usage(root)
    now = datetime.now(timezone.utc)
    newest_at = datetime.fromtimestamp(newest_mtime, timezone.utc) if newest_mtime else None
    data_age_seconds = int((now - newest_at).total_seconds()) if newest_at else None
    disk_used_pct = round(((usage.total - usage.free) / usage.total * 100) if usage.total else 0, 2)
    snapshot = _load_json(monitored[0])
    snapshot_ok = bool(snapshot and _snapshot_fresh(snapshot, 300))
    return {
        "dashboard_status": (
            "HEALTHY"
            if all(row["valid_json"] for row in integrity)
            and snapshot_ok
            and disk_used_pct < 95
            else "DEGRADED"
        ),
        "checked_at": now.isoformat(),
        "process_id": os.getpid(),
        "disk_total_bytes": usage.total,
        "disk_free_bytes": usage.free,
        "disk_used_pct": disk_used_pct,
        "latest_data_age_seconds": data_age_seconds,
        "paper_snapshot_fresh": snapshot_ok,
        "json_integrity": integrity,
        "read_only": True,
    }


def build_advanced_payload(root: Path) -> dict[str, Any]:
    return {
        "dashboard_stage": "DASH2.05-HOTFIX",
        "performance": performance_series(root),
        "events": event_log(root),
        "alerts": alerts(root),
        "health": dashboard_health(root),
        "read_only": True,
        "order_submission_enabled": False,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }


def _snapshot_fresh(payload: dict[str, Any], max_age: int) -> bool:
    raw = str(payload.get("observed_at", "")).strip()
    if not raw:
        return False
    try:
        observed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds() <= max_age


def _event_message(item: dict[str, Any]) -> str:
    pieces = [
        str(item.get("symbol", "")).strip(),
        str(item.get("side", item.get("approved_action", ""))).strip(),
        str(item.get("order_status", item.get("status", ""))).strip(),
    ]
    return " · ".join(part for part in pieces if part) or "Paper operation event"


def _alert(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
