from __future__ import annotations
import json
from pathlib import Path


PIPELINE = [
    ("credentials_profiles", "Credentials and Paper Profile"),
    ("market_polling", "Market Clock and Polling"),
    ("signals_strategy", "AI Signal Generation"),
    ("risk_approval", "Risk and Approval Gate"),
    ("order_submission", "Alpaca Paper Submission"),
    ("order_lifecycle", "Order and Fill Reconciliation"),
    ("positions_portfolio", "Position and Portfolio Sync"),
    ("session_orchestration", "Daily Autonomous Session"),
    ("restart_recovery", "Checkpoint, Lock, Watchdog and Recovery"),
    ("end_of_day", "End-of-Day Close and Certification"),
    ("monitoring_dashboard", "Monitoring and Operations Dashboard"),
    ("paper_completion", "P2/P3/P4/P5 Completion Certificate"),
]


def build_plan(audit: dict) -> dict:
    steps = []
    for index, (category, label) in enumerate(PIPELINE, start=1):
        selected = audit["canonical"][category]["selected"]
        steps.append({
            "sequence": index,
            "category": category,
            "label": label,
            "selected_path": selected["path"] if selected else None,
            "candidate_count": audit["canonical"][category][
                "candidate_count"
            ],
            "ready": selected is not None,
        })

    blockers = []
    if audit["missing_categories"]:
        blockers.append({
            "code": "MISSING_CANONICAL_CATEGORIES",
            "details": audit["missing_categories"],
        })

    unsafe_write_files = []
    for item in audit["write_capable_files"]:
        flags = item["safety_flags"]
        if (
            flags["contains_submit_order"]
            and not flags["mentions_paper_only"]
        ):
            unsafe_write_files.append(item["path"])

    if unsafe_write_files:
        blockers.append({
            "code": "WRITE_CAPABLE_FILES_REQUIRE_MANUAL_REVIEW",
            "details": unsafe_write_files,
        })

    return {
        "plan_name": "PAPER_TRADING_1_0_CANONICAL_OPERATION_PATH",
        "scope_locked": True,
        "new_feature_development_allowed": False,
        "tomorrow_actual_validation_excluded_today": True,
        "pipeline": steps,
        "today_completion_items": [
            "Repository-wide relevant-code scan",
            "Canonical component selection",
            "Exact duplicate detection",
            "Write-capable file inventory",
            "Premarket readiness gate",
            "Tomorrow market-day runbook generation",
        ],
        "tomorrow_only_items": [
            "Actual Alpaca Paper order submission",
            "Accepted/Filled lifecycle verification",
            "Position/account reconciliation",
            "P2/P3/P4 actual certification",
            "P5 long-run qualification start",
        ],
        "blockers": blockers,
        "status": "PASS" if not blockers else "REVIEW_REQUIRED",
    }


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
