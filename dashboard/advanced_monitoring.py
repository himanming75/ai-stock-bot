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

    equity = []
    drawdown = []
    for index, item in enumerate(points, start=1):
        if not isinstance(item, dict):
            continue
        trade_number = int(item.get("trade_number", index))
        equity.append({
            "x": trade_number,
            "y": _number(item.get("cumulative_pnl", 0)),
        })
        drawdown.append({
            "x": trade_number,
            "y": _number(item.get("drawdown", 0)),
        })

    if not equity:
        report = _load_json(
            root / "release/op2_17_to_op2_20/actual/daily_shadow_report.json"
        )
        equity = [{"x": 0, "y": 0.0}]
        drawdown = [{"x": 0, "y": _number(report.get("max_drawdown_pct", 0))}]

    return {"equity": equity, "drawdown": drawdown}


def event_log(root: Path, limit: int = 25) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    source_paths = [
        root / "release/op2_13_to_op2_16/actual/shadow_signal_queue.jsonl",
        root / "release/op2_01_to_op2_04/actual/shadow_decision_ledger.jsonl",
    ]
    for path in source_paths:
        for item in _load_jsonl(path, limit=limit):
            records.append({
                "timestamp": str(
                    item.get("created_at", item.get("observed_at", ""))
                ),
                "category": str(
                    item.get("stage", item.get("status", "EVENT"))
                ),
                "message": _event_message(item),
                "severity": "INFO",
            })

    runtime = _load_json(
        root / "release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json"
    )
    if runtime:
        records.append({
            "timestamp": str(runtime.get("observed_at", "")),
            "category": "RUNTIME",
            "message": str(runtime.get("state", "UNKNOWN")),
            "severity": (
                "ERROR"
                if runtime.get("safe_mode_engaged")
                else "INFO"
            ),
        })

    records.sort(key=lambda row: row.get("timestamp", ""), reverse=True)
    return records[:limit]


def alerts(root: Path) -> list[dict[str, Any]]:
    runtime = _load_json(
        root / "release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json"
    )
    pipeline = _load_json(
        root / "release/op2_13_to_op2_16/actual/automatic_shadow_signal_pipeline_result.json"
    )
    snapshot = _load_json(
        root / "release/op1_13_to_op1_16/actual/current_paper_snapshot.json"
    )

    output: list[dict[str, Any]] = []

    if runtime.get("safe_mode_engaged"):
        output.append(_alert("CRITICAL", "RUNTIME_SAFE_MODE", "Runtime safe mode is engaged."))
    elif str(runtime.get("state", "")).startswith("WAIT_"):
        output.append(_alert("WARNING", "RUNTIME_WAITING", str(runtime.get("state"))))

    if pipeline.get("safe_mode_engaged"):
        output.append(_alert("CRITICAL", "PIPELINE_SAFE_MODE", "Signal pipeline safe mode is engaged."))
    elif str(pipeline.get("state", "")).startswith("WAIT_"):
        output.append(_alert("WARNING", "PIPELINE_WAITING", str(pipeline.get("state"))))

    heartbeat = root / "release/op2_17_to_op2_20/actual/shadow_runtime_heartbeat.json"
    if not heartbeat.exists():
        output.append(_alert("WARNING", "HEARTBEAT_MISSING", "Runtime heartbeat is not available."))

    if not snapshot:
        output.append(_alert("WARNING", "SNAPSHOT_MISSING", "Current Paper snapshot is not available."))

    if runtime.get("error_count", 0):
        output.append(_alert(
            "CRITICAL",
            "RUNTIME_ERRORS",
            f'{int(runtime.get("error_count", 0))} runtime error(s) reported.',
        ))

    if not output:
        output.append(_alert("INFO", "SYSTEM_HEALTHY", "No active dashboard alerts."))
    return output


def dashboard_health(root: Path) -> dict[str, Any]:
    monitored = [
        root / "release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json",
        root / "release/op2_13_to_op2_16/actual/automatic_shadow_signal_pipeline_result.json",
        root / "release/op1_13_to_op1_16/actual/current_paper_snapshot.json",
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
    newest_at = (
        datetime.fromtimestamp(newest_mtime, timezone.utc)
        if newest_mtime
        else None
    )
    data_age_seconds = (
        int((now - newest_at).total_seconds())
        if newest_at
        else None
    )

    return {
        "dashboard_status": (
            "HEALTHY"
            if all(row["valid_json"] for row in integrity)
            else "DEGRADED"
        ),
        "checked_at": now.isoformat(),
        "process_id": os.getpid(),
        "disk_total_bytes": usage.total,
        "disk_free_bytes": usage.free,
        "disk_used_pct": round(
            ((usage.total - usage.free) / usage.total * 100)
            if usage.total
            else 0,
            2,
        ),
        "latest_data_age_seconds": data_age_seconds,
        "json_integrity": integrity,
        "read_only": True,
    }


def build_advanced_payload(root: Path) -> dict[str, Any]:
    return {
        "dashboard_stage": "DASH1.05-DASH1.08",
        "performance": performance_series(root),
        "events": event_log(root),
        "alerts": alerts(root),
        "health": dashboard_health(root),
        "read_only": True,
        "order_submission_enabled": False,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }


def _event_message(item: dict[str, Any]) -> str:
    symbol = str(item.get("symbol", "")).strip()
    action = str(item.get("action", item.get("approved_action", ""))).strip()
    status = str(item.get("status", "")).strip()
    pieces = [part for part in (symbol, action, status) if part]
    return " · ".join(pieces) or "Shadow operation event"


def _alert(severity: str, code: str, message: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message}


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
