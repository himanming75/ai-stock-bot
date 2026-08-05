from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .models import TradingProfile


def build_profile_catalog(profile_dir: Path) -> dict[str, Any]:
    profiles = []
    for path in sorted(profile_dir.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        profile = TradingProfile.from_dict(value)
        validation = profile.validate()
        profiles.append({
            "file": path.name,
            "profile_name": profile.profile_name,
            "broker_mode": profile.broker_mode,
            "horizon": profile.horizon,
            "enabled": profile.enabled,
            "allocation_enabled": profile.allocation_enabled,
            "multi_account_enabled": profile.multi_account_enabled,
            "valid": validation["valid"],
            "failed": validation["failed"],
        })

    return {
        "stage": "R4_PROFILE_CATALOG",
        "profile_count": len(profiles),
        "profiles": profiles,
        "all_profiles_valid": (
            bool(profiles)
            and all(item["valid"] for item in profiles)
        ),
        "actual_activation_performed": False,
        "broker_network_used": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
