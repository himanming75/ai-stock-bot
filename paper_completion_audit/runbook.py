from __future__ import annotations

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
    ("restart_recovery", "Checkpoint, Watchdog and Recovery"),
    ("end_of_day", "End-of-Day Processing"),
    ("monitoring_dashboard", "Monitoring and Operations"),
    ("paper_completion", "P2/P3/P4/P5 Completion"),
]


def build_markdown(result: dict) -> str:
    lines = [
        "# Paper Trading 1.0 Canonical Runtime Runbook",
        "",
        "## Locked scope",
        "",
        "- Existing code only",
        "- No new trading engine",
        "- No new AI features",
        "- No Live submission",
        "- Actual market-day validation remains tomorrow-only",
        "",
        "## Final canonical pipeline",
        "",
        "| # | Component | Selected runtime file | Alternatives |",
        "|---:|---|---|---:|",
    ]

    for index, (category, label) in enumerate(PIPELINE, start=1):
        selection = result["selected"][category]
        item = selection["selected"]
        path = item["path"] if item else "MISSING"
        lines.append(
            f"| {index} | {label} | `{path}` | "
            f"{len(selection['alternatives'])} |"
        )

    lines.extend([
        "",
        "## Tomorrow-only actual validation",
        "",
        "1. Load existing Alpaca Paper credentials.",
        "2. Run market-day preflight.",
        "3. Submit one controlled Paper order through the selected submission path.",
        "4. Capture the real client_order_id automatically.",
        "5. Reconcile order, fill, position, and account through the selected lifecycle path.",
        "6. Generate existing P2/P3/P4 certification.",
        "7. Start existing P5 long-run qualification.",
        "",
        "## Prohibited",
        "",
        "- Do not run alternative order-submission paths.",
        "- Do not use test, mock, offline, sandbox, or release copies.",
        "- Do not enable Live mode.",
        "- Do not run more than one controlled validation order.",
        "",
    ])

    if result["unsafe_selected_paths"]:
        lines.append("## Manual review required")
        lines.append("")
        for path in result["unsafe_selected_paths"]:
            lines.append(f"- `{path}`")
        lines.append("")

    return "\n".join(lines)


def save_markdown(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown(result), encoding="utf-8")
