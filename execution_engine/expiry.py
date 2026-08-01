from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import OrderIntent


@dataclass(frozen=True)
class IntentExpiryPolicy:
    def is_expired(self, intent: OrderIntent, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return now >= intent.expires_at
