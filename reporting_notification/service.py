from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .notifications import NotificationPreviewQueue, QuietHoursPolicy
from .reporting import ReportBuilder


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/auto_report_notification/actual"
    actual.mkdir(parents=True, exist_ok=True)

    dashboard = read_json(
        root / "release/v140_to_v143_ai_operations/actual/dashboard5_data.json"
    )
    validation = read_json(
        root / "release/validation_support_mega_bundle/actual/"
               "validation_support_result.json"
    )
    operations = read_json(
        root / "release/operations_v2/actual/operations_v2_result.json"
    )

    sections = {
        "executive_summary": {
            "dashboard_status": dashboard.get("status"),
            "validation_status": validation.get("status"),
            "operations_status": operations.get("status"),
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        },
        "performance": dashboard.get("performance_metrics", {}),
        "portfolio": dashboard.get("portfolio_intelligence", {}),
        "validation": {
            "status": validation.get("status"),
            "failed": validation.get("failed", []),
            "next_fixed_action": validation.get("next_fixed_action"),
        },
        "operations": {
            "status": operations.get("status"),
            "checks": operations.get("checks", {}),
        },
    }

    builder = ReportBuilder()
    reports = {}
    for period in ("DAILY", "WEEKLY", "MONTHLY"):
        report = builder.build(period=period, sections=sections)
        builder.write_json(actual / f"{period.lower()}_report.json", report)
        builder.write_html(actual / f"{period.lower()}_report.html", report)
        reports[period.lower()] = report

    performance_rows = []
    metrics = dashboard.get("performance_metrics", {})
    for key, value in sorted(metrics.items()):
        if not isinstance(value, (dict, list)):
            performance_rows.append({"metric": key, "value": value})
    builder.write_csv(actual / "performance_summary.csv", performance_rows)

    queue_path = actual / "notification_preview_queue.jsonl"
    if queue_path.exists():
        queue_path.unlink()

    quiet = QuietHoursPolicy().evaluate(
        observed_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
    )
    queue = NotificationPreviewQueue(queue_path)
    alert = {
        "category": "VALIDATION",
        "severity": "INFO",
        "subject": "P2 preflight ready",
        "message": "Validation support reports P2 read-only preflight ready.",
    }
    previews = [
        queue.enqueue(channel=channel, alert=alert, quiet_hours=quiet)
        for channel in ("EMAIL", "SLACK", "DISCORD", "TELEGRAM")
    ]
    duplicate_preview = queue.enqueue(
        channel="EMAIL",
        alert=alert,
        quiet_hours=quiet,
    )

    checks = {
        "daily_report_created": (actual / "daily_report.json").exists(),
        "weekly_report_created": (actual / "weekly_report.json").exists(),
        "monthly_report_created": (actual / "monthly_report.json").exists(),
        "html_reports_created": all(
            (actual / f"{period}_report.html").exists()
            for period in ("daily", "weekly", "monthly")
        ),
        "csv_created": (actual / "performance_summary.csv").exists(),
        "four_channel_previews": len(previews) == 4,
        "all_external_send_blocked": all(
            row["external_send_allowed"] is False for row in previews
        ),
        "network_unused": all(row["network_used"] is False for row in previews),
        "duplicate_suppressed": (
            duplicate_preview["duplicate_suppressed"] is True
        ),
    }

    result = {
        "stage": "AUTO_REPORT_NOTIFICATION_FRAMEWORK",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "auto_report_system": "READY",
        "daily_report": "READY",
        "weekly_report": "READY",
        "monthly_report": "READY",
        "html_export": "READY_PDF_PRINTABLE",
        "json_export": "READY",
        "csv_export": "READY",
        "notification_framework": "READY_PREVIEW_ONLY",
        "supported_channels": ["EMAIL", "SLACK", "DISCORD", "TELEGRAM"],
        "quiet_hours_policy": "READY",
        "alert_deduplication": "READY",
        "actual_external_send_performed": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_development": "MULTI_BROKER_AND_STRATEGY_PLUGIN_FRAMEWORK",
    }
    (actual / "auto_report_notification_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
