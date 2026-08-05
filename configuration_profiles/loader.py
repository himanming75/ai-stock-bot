from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .gates import evaluate_profile_activation_gate
from .models import TradingProfile


def load_profile(path: Path) -> tuple[TradingProfile, dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    profile = TradingProfile.from_dict(value)
    validation = profile.validate()
    return profile, validation


def preview_profile_activation(
    root: Path,
    profile_path: Path,
) -> dict[str, Any]:
    profile, validation = load_profile(profile_path)
    gate = evaluate_profile_activation_gate(
        root,
        broker_mode=profile.broker_mode,
    )
    preview_allowed = (
        validation["valid"]
        and gate["activation_preview_allowed"]
        and profile.enabled
    )
    return {
        "stage": "R4_PROFILE_ACTIVATION_PREVIEW",
        "profile_name": profile.profile_name,
        "broker_mode": profile.broker_mode,
        "horizon": profile.horizon,
        "profile_valid": validation["valid"],
        "validation": validation,
        "gate": gate,
        "preview_allowed": preview_allowed,
        "actual_activation_performed": False,
        "broker_network_used": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
