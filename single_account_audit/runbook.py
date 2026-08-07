from __future__ import annotations

from pathlib import Path


ORDER = [
    "alpaca_paper_account_binding",
    "etrade_live_account_binding",
    "account_id_allowlist",
    "broker_account_role_lock",
    "pre_order_account_validation",
    "credential_account_match",
    "restart_account_revalidation",
    "checkpoint_account_identity",
    "dashboard_account_visibility",
    "wrong_account_hard_block",
    "single_account_runtime_lock",
    "account_switch_prohibition",
]


def build_markdown(result: dict) -> str:
    lines = [
        "# Phase 4 Single Account Binding Runbook",
        "",
        "## Fixed account roles",
        "",
        "- Alpaca: one Paper account only",
        "- E*TRADE: one Live account only",
        "- Multi-account operation: disabled",
        "- Runtime account switching: disabled",
        "- Automatic account selection: disabled",
        "",
        "## Safety state",
        "",
        "- E*TRADE Live submission: OFF",
        "- Paper orders during build: 0",
        "- Live orders during build: 0",
        "",
        "## Canonical account safety pipeline",
        "",
        "| # | Capability | Selected path | Candidates |",
        "|---:|---|---|---:|",
    ]

    for index, capability in enumerate(ORDER, start=1):
        entry = result["selected"][capability]
        selected = entry["selected"]
        path = selected["path"] if selected else "MISSING"
        lines.append(
            f"| {index} | {entry['label']} | `{path}` | "
            f"{entry['candidate_count']} |"
        )

    lines.extend([
        "",
        "## Operating rule",
        "",
        "Every startup and every order attempt must confirm broker, mode, "
        "credential identity, and allowed account identity. Any mismatch "
        "must hard-block order creation and submission.",
        "",
        "## Deferred",
        "",
    ])

    for item in result["deferred_until_after_operation"]:
        lines.append(f"- {item}")

    return "\n".join(lines) + "\n"


def save_markdown(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown(result), encoding="utf-8")
