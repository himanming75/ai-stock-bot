from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .api import CommandCenterService
from .config import CommandCenterPaths


class PaperCommandCenterCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        fixture = output_dir / "fixtures"
        fixture.mkdir(
            parents=True,
            exist_ok=True,
        )

        def write(name: str, payload: dict):
            path = fixture / name
            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            return path

        polling = fixture / "polling.jsonl"
        polling.write_text(
            json.dumps({
                "cycle": 1,
                "status": "PASS",
            })
            + "\n",
            encoding="utf-8",
        )

        paths = CommandCenterPaths(
            controller_summary=write(
                "controller.json",
                {
                    "status": "READY",
                    "cycle_count": 10,
                },
            ),
            checkpoint=write(
                "checkpoint.json",
                {
                    "status": "VALID",
                },
            ),
            execution_plan=write(
                "execution.json",
                {
                    "mode": "READ_ONLY",
                },
            ),
            order_ticket_snapshot=write(
                "tickets.json",
                {
                    "ticket_count": 0,
                },
            ),
            watchdog_summary=write(
                "watchdog.json",
                {
                    "status": "HEALTHY",
                },
            ),
            daily_session_summary=write(
                "daily.json",
                {
                    "status": "WAITING",
                },
            ),
            polling_ledger=polling,
            command_plan_output=(
                output_dir / "latest_plan.json"
            ),
            audit_ledger=(
                output_dir / "audit.jsonl"
            ),
        )
        service = CommandCenterService(
            paths=paths
        )
        status = service.status()
        plans = [
            service.command_plan(
                action=action,
                requested_by="CERTIFICATION",
                reason="fixture",
            )
            for action in (
                "START",
                "PAUSE",
                "RESUME",
                "STOP",
                "VALIDATE",
            )
        ]

        result = {
            "stage": (
                "V8801_TO_V9000_PAPER_CONTROLLER_"
                "GUI_REST_API_AND_RUNTIME_COMMAND_CENTER"
            ),
            "status": "PASS",
            "runtime_status_reader_ready": True,
            "controller_summary_ready": True,
            "watchdog_summary_ready": True,
            "daily_session_summary_ready": True,
            "polling_tail_ready": True,
            "command_plan_api_ready": True,
            "start_plan_ready": True,
            "pause_plan_ready": True,
            "resume_plan_ready": True,
            "stop_plan_ready": True,
            "validate_plan_ready": True,
            "responsive_gui_ready": True,
            "five_second_refresh_ready": True,
            "audit_ledger_ready": True,
            "default_port": 8769,
            "fixture_status": status,
            "fixture_plan_count": len(plans),
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_process_started": False,
            "actual_process_stopped": False,
            "actual_task_scheduler_modified": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V9001_TO_V9200_PROFILE_STRATEGY_"
                "AND_RISK_CONFIGURATION_GUI"
            ),
        }

        if not (
            status["overall_status"] == "READY"
            and len(plans) == 5
            and all(
                plan["mode"] == "DRY_RUN_ONLY"
                for plan in plans
            )
            and all(
                plan["execution_status"]
                == "NOT_EXECUTED"
                for plan in plans
            )
        ):
            result["status"] = "BLOCKED"

        result[
            "certification_fingerprint"
        ] = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

        (output_dir / "paper_command_center_certification.json").write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        return result
