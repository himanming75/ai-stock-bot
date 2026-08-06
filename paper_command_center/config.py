from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandCenterPaths:
    controller_summary: Path
    checkpoint: Path
    execution_plan: Path
    order_ticket_snapshot: Path
    watchdog_summary: Path
    daily_session_summary: Path
    polling_ledger: Path
    command_plan_output: Path
    audit_ledger: Path

    def to_dict(self) -> dict[str, str]:
        return {
            key: str(value)
            for key, value in asdict(self).items()
        }


def default_paths() -> CommandCenterPaths:
    return CommandCenterPaths(
        controller_summary=Path(
            "release/paper_automation_controller/actual/"
            "controller_summary.json"
        ),
        checkpoint=Path(
            "release/paper_automation_controller/actual/"
            "checkpoint.json"
        ),
        execution_plan=Path(
            "release/paper_automation_controller/actual/"
            "execution_plan_snapshot.json"
        ),
        order_ticket_snapshot=Path(
            "release/paper_automation_controller/actual/"
            "order_ticket_snapshot.json"
        ),
        watchdog_summary=Path(
            "release/automation_watchdog_restart_recovery/"
            "actual/watchdog_summary.json"
        ),
        daily_session_summary=Path(
            "release/daily_session_manager_startup_autorun/"
            "actual/daily_session_summary.json"
        ),
        polling_ledger=Path(
            "release/actual_market_polling_validation/actual/"
            "polling_ledger.jsonl"
        ),
        command_plan_output=Path(
            "release/paper_command_center/actual/"
            "latest_command_plan.json"
        ),
        audit_ledger=Path(
            "release/paper_command_center/actual/"
            "command_center_audit.jsonl"
        ),
    )
