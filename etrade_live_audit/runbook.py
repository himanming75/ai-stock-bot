from __future__ import annotations

from pathlib import Path


ORDER = [
    "oauth_authentication",
    "production_endpoint",
    "credential_separation",
    "accounts_read",
    "positions_read",
    "market_data_read",
    "order_preview",
    "order_place",
    "order_status",
    "order_cancel",
    "duplicate_prevention",
    "risk_limits",
    "kill_switch",
    "restart_reconciliation",
]


def build_markdown(result: dict) -> str:
    lines = [
        "# Phase 3 E*TRADE Live Canonical Runbook",
        "",
        "## Fixed broker roles",
        "",
        "- Alpaca: Paper trading only",
        "- E*TRADE: Live trading only",
        "- Other brokers: Disabled and deferred",
        "",
        "## Current safety state",
        "",
        "- E*TRADE live submission: OFF",
        "- E*TRADE live cancellation: OFF",
        "- E*TRADE capital allocation: OFF",
        "- Actual live orders during build: 0",
        "",
        "## Canonical E*TRADE live pipeline",
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
        "## Required activation sequence after Alpaca Paper qualification",
        "",
        "1. Obtain E*TRADE Production consumer key and sign required agreements.",
        "2. Complete OAuth authorization for the live account.",
        "3. Verify account, balance, positions, and market data in read-only mode.",
        "4. Verify Preview Order only.",
        "5. Enable one controlled live order with strict limits.",
        "6. Reconcile order, fill, position, and account.",
        "7. Disable live write immediately after first validation.",
        "8. Review results before limited autonomous live operation.",
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
