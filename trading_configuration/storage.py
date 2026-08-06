from __future__ import annotations
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


def save_draft(
    *,
    draft: dict,
    draft_path: Path,
    ledger_path: Path,
) -> dict:
    now = datetime.now(
        timezone.utc
    ).isoformat()
    result = {
        "draft_id": (
            f"draft_{secrets.token_hex(8)}"
        ),
        "created_at": now,
        "status": "DRAFT_SAVED",
        "approval_status": "REVIEW_REQUIRED",
        "activation_status": "NOT_ACTIVATED",
        **draft,
    }

    draft_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    draft_path.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    with ledger_path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                {
                    "draft_id": result[
                        "draft_id"
                    ],
                    "created_at": now,
                    "profile_key": result[
                        "profile_key"
                    ],
                    "symbol_count": len(
                        result["symbols"]
                    ),
                    "status": "DRAFT_SAVED",
                    "activation_status": (
                        "NOT_ACTIVATED"
                    ),
                    "broker_write_enabled": False,
                    "order_submission_enabled": False,
                },
                sort_keys=True,
            )
            + "\n"
        )
    return result


def load_draft(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
        return value if isinstance(
            value,
            dict,
        ) else {}
    except Exception:
        return {}
