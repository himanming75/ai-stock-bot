from __future__ import annotations
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .i18n import bilingual
from .io import append_jsonl, write_json


CHANNELS = {
    "EMAIL",
    "SLACK",
    "DISCORD",
    "WEB",
}


def build_notification_preview(
    *,
    channel: str,
    event_type: str,
    severity: str,
    title_en: str,
    title_ko: str,
    message_en: str,
    message_ko: str,
    output_path: Path,
    ledger_path: Path,
) -> dict:
    normalized = channel.upper()
    if normalized not in CHANNELS:
        raise ValueError(
            "UNSUPPORTED_NOTIFICATION_CHANNEL"
        )

    now = datetime.now(
        timezone.utc
    ).isoformat()
    preview = {
        "notification_id": (
            f"notify_{secrets.token_hex(8)}"
        ),
        "created_at": now,
        "channel": normalized,
        "event_type": event_type.upper(),
        "severity": severity.upper(),
        "title": {
            "en": title_en,
            "ko": title_ko,
        },
        "message": {
            "en": message_en,
            "ko": message_ko,
        },
        "status": "REVIEW_REQUIRED",
        "status_i18n": bilingual(
            "REVIEW_REQUIRED"
        ),
        "mode": "PREVIEW_ONLY",
        "delivery_status": "NOT_SENT",
        "external_network_enabled": False,
        "email_send_enabled": False,
        "slack_send_enabled": False,
        "discord_send_enabled": False,
        "broker_write_enabled": False,
    }
    write_json(output_path, preview)
    append_jsonl(
        ledger_path,
        {
            "notification_id": preview[
                "notification_id"
            ],
            "created_at": now,
            "channel": normalized,
            "delivery_status": "NOT_SENT",
            "event_type": preview[
                "event_type"
            ],
        },
    )
    return preview


def send_notification(*args, **kwargs):
    raise PermissionError(
        "NOTIFICATION_DELIVERY_DISABLED"
    )
