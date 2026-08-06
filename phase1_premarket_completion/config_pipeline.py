from __future__ import annotations
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .i18n import bilingual
from .io import append_jsonl, read_json, write_json


def _fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def create_review_package(
    *,
    draft_path: Path,
    output_path: Path,
    ledger_path: Path,
    requested_by: str,
) -> dict:
    draft = read_json(draft_path)
    if not draft:
        raise ValueError(
            "CONFIGURATION_DRAFT_NOT_FOUND"
        )

    execution = draft.get("execution", {})
    if not isinstance(execution, dict):
        execution = {}

    # Never trust a draft's execution flags.
    safe_execution = {
        "mode": "REVIEW_PACKAGE_ONLY",
        "activation_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "order_cancel_enabled": False,
    }

    now = datetime.now(
        timezone.utc
    ).isoformat()
    package = {
        "review_id": (
            f"review_{secrets.token_hex(8)}"
        ),
        "created_at": now,
        "requested_by": (
            requested_by.strip() or "LOCAL_USER"
        ),
        "status": "REVIEW_REQUIRED",
        "status_i18n": bilingual(
            "REVIEW_REQUIRED"
        ),
        "draft_fingerprint": _fingerprint(
            draft
        ),
        "draft": draft,
        "safe_execution": safe_execution,
        "activation_status": "NOT_ACTIVATED",
        "activation_status_i18n": bilingual(
            "NOT_ACTIVATED"
        ),
    }
    write_json(output_path, package)
    append_jsonl(
        ledger_path,
        {
            "review_id": package["review_id"],
            "created_at": now,
            "status": package["status"],
            "draft_fingerprint": package[
                "draft_fingerprint"
            ],
            "activation_status": (
                "NOT_ACTIVATED"
            ),
        },
    )
    return package


def create_approval_candidate(
    *,
    review_path: Path,
    output_path: Path,
    ledger_path: Path,
    approved_by: str,
    approval_note: str,
) -> dict:
    review = read_json(review_path)
    if not review:
        raise ValueError(
            "REVIEW_PACKAGE_NOT_FOUND"
        )
    if (
        review.get("status")
        != "REVIEW_REQUIRED"
    ):
        raise ValueError(
            "INVALID_REVIEW_STATUS"
        )

    now = datetime.now(
        timezone.utc
    ).isoformat()
    candidate = {
        "candidate_id": (
            f"candidate_{secrets.token_hex(8)}"
        ),
        "created_at": now,
        "approved_by": (
            approved_by.strip() or "LOCAL_USER"
        ),
        "approval_note": approval_note.strip(),
        "status": "APPROVED_CANDIDATE",
        "status_i18n": bilingual(
            "APPROVED_CANDIDATE"
        ),
        "review_id": review["review_id"],
        "draft_fingerprint": review[
            "draft_fingerprint"
        ],
        "configuration": review["draft"],
        "activation_status": "NOT_ACTIVATED",
        "activation_status_i18n": bilingual(
            "NOT_ACTIVATED"
        ),
        "runtime_apply_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "order_cancel_enabled": False,
    }
    write_json(output_path, candidate)
    append_jsonl(
        ledger_path,
        {
            "candidate_id": candidate[
                "candidate_id"
            ],
            "created_at": now,
            "status": candidate["status"],
            "review_id": candidate[
                "review_id"
            ],
            "activation_status": (
                "NOT_ACTIVATED"
            ),
        },
    )
    return candidate


def activate_candidate(*args, **kwargs):
    raise PermissionError(
        "CONFIGURATION_ACTIVATION_DISABLED"
    )
