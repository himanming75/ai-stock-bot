from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .extractors import (
    controller_events,
    health_events,
    performance_events,
    risk_events,
)
from .io import (
    append_jsonl,
    read_json,
    read_json_optional,
    read_jsonl,
)
from .models import (
    SEVERITY_RANK,
    event_key,
    message_id,
)
from .routing import delivery_plan


class NotificationAlertRoutingService:
    def evaluate(
        self,
        *,
        risk_path: Path,
        health_path: Path,
        performance_path: Path,
        controller_path: Path,
        policy_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        policy = read_json(policy_path)
        risk = read_json_optional(risk_path)
        health = read_json_optional(health_path)
        performance = read_json_optional(performance_path)
        controller = read_json_optional(controller_path)

        events = (
            risk_events(risk)
            + health_events(health)
            + performance_events(performance)
            + controller_events(controller)
        )

        prior = read_jsonl(
            output_dir / "notification_ledger.jsonl"
        )
        last_by_key = {}
        for item in prior:
            key = item.get("deduplication_key")
            generated_at = item.get("generated_at")
            if key and generated_at:
                last_by_key[key] = generated_at

        cooldown = int(
            policy.get("deduplication_cooldown_seconds", 900)
        )
        queue = []
        suppressed = []

        for event in events:
            key = event_key(
                event["source"],
                event["code"],
                event.get("context", {}),
            )
            previous = last_by_key.get(key)
            suppress = False
            if previous:
                try:
                    previous_time = datetime.fromisoformat(
                        previous.replace("Z", "+00:00")
                    )
                    suppress = (
                        now - previous_time
                    ).total_seconds() < cooldown
                except ValueError:
                    suppress = False

            generated_at = now.isoformat()
            record = {
                **event,
                "message_id": message_id(
                    key, generated_at
                ),
                "deduplication_key": key,
                "generated_at": generated_at,
                "delivery_plan": delivery_plan(
                    event, policy
                ),
                "actual_send_performed": False,
                "email_sent": False,
                "slack_sent": False,
                "discord_sent": False,
                "webhook_sent": False,
                "status": (
                    "SUPPRESSED_DUPLICATE"
                    if suppress
                    else "QUEUED_PREPARE_ONLY"
                ),
            }
            if suppress:
                suppressed.append(record)
            else:
                queue.append(record)
                append_jsonl(
                    output_dir
                    / "notification_ledger.jsonl",
                    record,
                )

        queue.sort(
            key=lambda item: SEVERITY_RANK.get(
                item["severity"], 0
            ),
            reverse=True,
        )

        counts = {
            severity: sum(
                1
                for item in queue
                if item["severity"] == severity
            )
            for severity in (
                "CRITICAL",
                "WARNING",
                "INFO",
            )
        }

        daily_summary = {
            "date": now.date().isoformat(),
            "generated_at": now.isoformat(),
            "queued_count": len(queue),
            "suppressed_count": len(suppressed),
            "critical_count": counts["CRITICAL"],
            "warning_count": counts["WARNING"],
            "info_count": counts["INFO"],
            "risk_level": risk.get("risk_level"),
            "health_status": health.get("status"),
            "health_score": health.get("health_score"),
            "performance_status": performance.get("status"),
            "controller_status": controller.get("status"),
            "actual_send_performed": False,
        }

        output_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "stage": (
                "V361_TO_V370_NOTIFICATION_AND_ALERT_ROUTING"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "queue": queue,
            "suppressed_duplicates": suppressed,
            "queued_count": len(queue),
            "suppressed_count": len(suppressed),
            "severity_counts": counts,
            "daily_summary": daily_summary,
            "delivery_mode": "PREPARE_ONLY",
            "channels": policy.get("channel_enabled", {}),
            "actual_external_network_used": False,
            "actual_notification_send_performed": False,
            "actual_email_sent": 0,
            "actual_slack_messages_sent": 0,
            "actual_discord_messages_sent": 0,
            "actual_webhooks_sent": 0,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V371_TO_V380_AUTONOMOUS_PAPER_OPERATIONS_GATE"
            ),
        }

        (
            output_dir / "notification_queue.json"
        ).write_text(
            json.dumps(
                queue, indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        (
            output_dir / "notification_summary.json"
        ).write_text(
            json.dumps(
                result, indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        (
            output_dir / "daily_notification_digest.json"
        ).write_text(
            json.dumps(
                daily_summary,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (
            output_dir / "notification_dashboard.json"
        ).write_text(
            json.dumps(
                {
                    "generated_at": now.isoformat(),
                    "delivery_mode": "PREPARE_ONLY",
                    "queued_count": len(queue),
                    "suppressed_count": len(suppressed),
                    "severity_counts": counts,
                    "top_alerts": queue[:10],
                    "actual_send_performed": False,
                    "broker_write": False,
                    "paper_orders_submitted": 0,
                    "live_orders_submitted": 0,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return result
