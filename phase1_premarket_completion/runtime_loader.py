from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .i18n import bilingual
from .io import read_json, write_json


def build_runtime_load_plan(
    *,
    candidate_path: Path,
    current_runtime_path: Path,
    output_path: Path,
) -> dict:
    candidate = read_json(candidate_path)
    if not candidate:
        raise ValueError(
            "APPROVED_CANDIDATE_NOT_FOUND"
        )
    if (
        candidate.get("status")
        != "APPROVED_CANDIDATE"
    ):
        raise ValueError(
            "INVALID_CANDIDATE_STATUS"
        )

    current = read_json(
        current_runtime_path
    )
    configuration = candidate.get(
        "configuration",
        {},
    )
    payload = {
        "candidate_id": candidate[
            "candidate_id"
        ],
        "configuration": configuration,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    plan = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": "READY",
        "status_i18n": bilingual("READY"),
        "mode": "HOT_RELOAD_PLAN_ONLY",
        "candidate_id": candidate[
            "candidate_id"
        ],
        "candidate_fingerprint": fingerprint,
        "current_runtime_available": bool(
            current
        ),
        "diff_summary": {
            "profile_key": configuration.get(
                "profile_key"
            ),
            "symbol_count": len(
                configuration.get(
                    "symbols",
                    [],
                )
            ),
            "enabled_strategies": sorted(
                name
                for name, item in (
                    configuration.get(
                        "strategies",
                        {},
                    )
                    or {}
                ).items()
                if isinstance(item, dict)
                and item.get("enabled")
            ),
        },
        "validation_checks": {
            "candidate_status_valid": True,
            "broker_write_false": True,
            "order_submission_false": True,
            "activation_false": True,
        },
        "runtime_apply_enabled": False,
        "process_reload_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
    }
    write_json(output_path, plan)
    return plan


def apply_runtime_plan(*args, **kwargs):
    raise PermissionError(
        "RUNTIME_CONFIGURATION_APPLY_DISABLED"
    )
