from __future__ import annotations
import secrets
from collections import deque

from .models import Notification


class NotificationQueue:
    def __init__(self) -> None:
        self.items: deque[Notification] = deque()

    def enqueue(
        self,
        *,
        channel: str,
        severity: str,
        subject: str,
        body: str,
    ) -> Notification:
        item = Notification(
            notification_id=(
                f"ntf_{secrets.token_hex(8)}"
            ),
            channel=channel.upper(),
            severity=severity.upper(),
            subject=subject,
            body=body,
            status="PENDING",
            attempts=0,
        )
        self.items.append(item)
        return item

    def list_items(self) -> list[dict]:
        return [
            item.to_dict()
            for item in self.items
        ]


class MockNotificationAdapter:
    def __init__(self, channel: str) -> None:
        self.channel = channel.upper()
        self.deliveries: list[dict] = []

    def deliver(
        self,
        notification: Notification,
    ) -> dict:
        if (
            notification.channel.upper()
            != self.channel
        ):
            return {
                "status": "BLOCKED",
                "reason": "CHANNEL_MISMATCH",
                "external_delivery_performed": False,
            }
        payload = {
            "notification_id": (
                notification.notification_id
            ),
            "channel": self.channel,
            "status": "MOCK_DELIVERED",
            "external_delivery_performed": False,
        }
        self.deliveries.append(payload)
        return payload
